import json
import time
from pathlib import Path
from typing import Any

import pandas as pd
from tqdm.auto import tqdm

from rag.templates import GROUND_TRUTH_PROMPT
from src.core.config import ElasticsearchConfig
from src.core.utils.logger import setup_logger
from src.elastic.client import get_elasticsearch_client
from src.elastic.queries import build_all_documents_query

logger = setup_logger(__name__)

def generate_questions(doc):
    prompt = GROUND_TRUTH_PROMPT.format(**doc)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    json_response = response.choices[0].message.content

    try:
        # Try to parse and validate the response
        questions = json.loads(json_response)

        # Validate that we got a list of exactly 5 questions
        if not isinstance(questions, list):
            raise ValueError("Response is not a list")
        if len(questions) != 5:
            raise ValueError(f"Expected 5 questions, got {len(questions)}")
        if not all(isinstance(q, str) for q in questions):
            raise ValueError("All items must be strings")

        return json_response

    except Exception as e:
        logger.log_error(
            f"Failed to parse GPT response for document {doc['id']}",
            ex=e,
            extra={
                "document_id": doc["id"],
                "raw_response": json_response,
                "prompt": prompt
            }
        )
        raise
def process_document(doc: dict[str, Any], max_retries: int = 3) -> list[tuple[str, str, str]]:
    """Process a single document with retry logic.
    Returns a list of tuples (question, course, document_id).
    """
    retries = 0
    while retries < max_retries:
        try:
            questions = generate_questions(doc)
            questions_data = json.loads(questions)

            # Handle both list and object formats
            if isinstance(questions_data, list):
                questions_list = questions_data
            elif isinstance(questions_data, dict):
                questions_list = [v for v in questions_data.values()]
            else:
                raise ValueError(f"Unexpected response format: {type(questions_data)}")

            return [
                (generated_question, doc["course"], doc["id"])
                for generated_question in questions_list
            ]

        except Exception as e:
            retries += 1
            if retries == max_retries:
                logger.log_error(
                    f"Failed to process document after {max_retries} attempts",
                    ex=e,
                    extra={
                        "document_id": doc["id"],
                        "raw_response": questions if "questions" in locals() else None
                    }
                )
                return []  # Return empty list on failure

            # Wait before retrying (exponential backoff)
            time.sleep(2 ** retries)

    return []  # Should never reach here, but just in case

def process_all_documents() -> list[tuple[str, str, str]]:
    """Retrieves all documents from Elasticsearch and generates questions for each one.
    Returns a list of tuples (question, course, document_id).
    """
    es = get_elasticsearch_client()
    es_config = ElasticsearchConfig()

    # Search for all documents using the specific query
    query = build_all_documents_query()

    try:
        # Fetch the documents
        response = es.search(
            index=es_config.index_name,
            body=query
        )

        results = []
        failed_docs = []

        # Process each document
        for hit in tqdm(response["hits"]["hits"], desc="Generating questions"):
            doc = hit["_source"]
            doc_results = process_document(doc)

            if doc_results:
                results.extend(doc_results)
            else:
                failed_docs.append(doc["id"])

        # Log summary
        total_docs = len(response["hits"]["hits"])
        failed_count = len(failed_docs)
        success_rate = ((total_docs - failed_count) / total_docs) * 100

        logger.log_info(
            "Processing summary",
            extra={
                "total_documents": total_docs,
                "failed_documents": failed_count,
                "success_rate": f"{success_rate:.2f}%",
                "failed_doc_ids": failed_docs
            }
        )

        return results

    except Exception as e:
        logger.log_error("Failed to fetch documents from Elasticsearch", ex=e)
        raise

if __name__ == "__main__":
    # Create output directory if it doesn't exist
    output_dir = Path("data/output")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process the documents
    results = process_all_documents()

    # Create DataFrame with correct columns
    df = pd.DataFrame(results, columns=["question", "course", "document"])

    # Save results to CSV
    output_file = output_dir / "ground-truth-data.csv"
    df.to_csv(output_file, index=False)

    logger.log_info(f"Ground truth data saved to {output_file}")
    logger.log_info(f"Total questions generated: {len(df)}")
