import json
import hashlib
from typing import Any

from elasticsearch import Elasticsearch
from tqdm.auto import tqdm

from src.core.config import ElasticsearchConfig
from src.core.utils.logger import setup_logger
from src.elastic.client import get_elasticsearch_client
from src.models.embedding import embed_text
from src.utils.text_cleaner import clean_text_for_json

logger = setup_logger(__name__)

def generate_hash_id(doc: dict[str, Any]) -> str:
    """Generate a unique hash ID for a document.

    Args:
        doc: Dictionary containing document data with 'course', 'question', and 'text' fields.

    Returns:
        str: An 8-character hexadecimal hash string based on document content.
    """
    combined = f"{doc['course']}-{doc['question']}-{doc['text'][:12]}"
    hash_object = hashlib.md5(combined.encode())
    hash_hex = hash_object.hexdigest()
    document_id = hash_hex[:8]
    
    return document_id

def load_documents(file_path: str) -> list[dict[str, Any]]:
    """Load and process documents from a JSON file.

    This function reads a JSON file containing course documents, processes each document by:
    1. Cleaning text fields
    2. Adding course information
    3. Generating unique document IDs
    4. Creating vector embeddings for text fields

    Args:
        file_path: Path to the JSON file containing documents in the format:
                  [{"course": "course_name", "documents": [{...}, ...]}]

    Returns:
        list[dict[str, Any]]: List of processed documents with the following fields:
            - text: Cleaned text content
            - question: Cleaned question text
            - course: Course name
            - id: Unique document hash
            - text_vector: Vector embedding of text
            - question_vector: Vector embedding of question
            - question_text_vector: Vector embedding of combined question and text

    Raises:
        FileNotFoundError: If the specified file does not exist
        json.JSONDecodeError: If the file contains invalid JSON
        KeyError: If required fields are missing in the JSON structure
    """
    try:
        with open(file_path, encoding='utf-8') as f_in:
            raw_documents = json.load(f_in)

        documents = []
        for course in raw_documents:
            course_name = course["course"]
            for doc in course["documents"]:
                try:
                    # Clean text fields before processing
                    doc["text"] = clean_text_for_json(doc["text"])
                    doc["question"] = clean_text_for_json(doc["question"])
                    # Course name don't have any problems
                    doc["course"] = course_name
                    # Create hash id
                    doc["id"] = generate_hash_id(doc)
                    # Create question + text
                    question_text = f"{doc['question']} {doc['text']}"
                    # Add embedding for the text
                    doc["text_vector"] = embed_text(doc["text"])
                    doc['question_vector'] = embed_text(doc["question"])
                    doc['question_text_vector'] = embed_text(question_text)
                    documents.append(doc)
                except KeyError as e:
                    logger.log_error(f"Missing required field in document: {e}", ex=e)
                    continue
                except Exception as e:
                    logger.log_error(f"Error processing document: {e}", ex=e)
                    continue

        if not documents:
            logger.log_warning("No documents were successfully processed")
            
        return documents
    except FileNotFoundError as e:
        logger.log_error(f"File not found: {file_path}", ex=e)
        raise
    except json.JSONDecodeError as e:
        logger.log_error(f"Invalid JSON in file {file_path}", ex=e)
        raise
    except Exception as e:
        logger.log_error(f"Unexpected error loading documents from {file_path}", ex=e)
        raise

def create_index(es: Elasticsearch, es_config: ElasticsearchConfig) -> None:
    """Create an Elasticsearch index with specified settings.

    Args:
        es: Elasticsearch client instance.
        es_config: Configuration object containing index settings and name.

    Raises:
        Exception: If index creation fails.
    """
    try:
        logger.log_info(es_config.index_settings)

        es.indices.create(
            index=es_config.index_name,
            body=es_config.index_settings,
        )
        logger.log_info(f"Created index: {es_config.index_name}")
    except Exception as e:
        logger.log_error(f"Failed to create index {es_config.index_name}", ex=e)
        raise

def delete_index(es: Elasticsearch, es_config: ElasticsearchConfig) -> None:
    """Delete an Elasticsearch index if it exists.

    Args:
        es: Elasticsearch client instance.
        es_config: Configuration object containing index name.

    Raises:
        Exception: If index deletion fails.
    """
    try:
        if es.indices.exists(index=es_config.index_name):
            es.indices.delete(index=es_config.index_name)
            logger.log_info(f"Deleted index: {es_config.index_name}")
        else:
            logger.log_info(f"Index {es_config.index_name} does not exist, skipping deletion")
    except Exception as e:
        logger.log_error(f"Failed to delete index {es_config.index_name}", ex=e)
        raise

def index_documents(file_path: str) -> None:
    """Index documents from a JSON file into Elasticsearch.

    This function performs the following steps:
    1. Loads documents from the specified file
    2. Deletes existing index if present
    3. Creates a new index with proper settings
    4. Indexes each document with its text and vector embeddings

    Args:
        file_path: Path to JSON file containing documents to index.

    Raises:
        Exception: If document indexing fails.
    """
    es = get_elasticsearch_client()
    documents = load_documents(file_path)
    es_config = ElasticsearchConfig()

    delete_index(es, es_config)
    create_index(es, es_config)

    for doc in tqdm(documents):
        try:
            es.index(
                index=es_config.index_name,
                document={
                    "text": doc["text"],
                    "section": doc["section"],
                    "question": doc["question"],
                    "course": doc["course"],
                    "text_vector": doc["text_vector"],
                    "question_vector": doc["question_vector"],
                    "question_text_vector": doc["question_text_vector"],
                    "id": doc["id"]
                },
                error_trace=True
            )
        except Exception as e:
            logger.log_error("Failed to index document", ex=e)
            raise


if __name__ == "__main__":
    DOCUMENTS_FILE = "data/input/faqs/documents.json"
    index_documents(DOCUMENTS_FILE)
