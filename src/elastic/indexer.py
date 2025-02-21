import json
import hashlib
from typing import Any

from elasticsearch import Elasticsearch
from tqdm.auto import tqdm

from src.core.config import ElasticsearchConfig
from src.core.utils.logger import setup_logger
from src.elastic.client import get_elasticsearch_client
from src.models.embedding import embed_text

logger = setup_logger(__name__)

def generate_hash_id(doc: dict[str, Any]) -> str:
    combined = f"{doc['course']}-{doc['question']}-{doc['text'][:12]}"
    hash_object = hashlib.md5(combined.encode())
    hash_hex = hash_object.hexdigest()
    document_id = hash_hex[:8]
    
    return document_id

def load_documents(file_path: str) -> list[dict[str, Any]]:
    with open(file_path) as f_in:
        documents_file = json.load(f_in)

    documents = []
    for course in documents_file:
        course_name = course["course"]
        for doc in course["documents"]:
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

    return documents

def create_index(es: Elasticsearch, es_config: ElasticsearchConfig) -> None:
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
    try:
        if es.indices.exists(index=es_config.index_name):
            es.indices.delete(index=es_config.index_name)
            logger.log_info(f"Deleted index: {es_config.index_name}")
        else:
            logger.log_info(f"Index {es_config.index_name} does not exist, skipping deletion")
    except Exception as e:
        logger.log_error(f"Failed to delete index {es_config.index_name}", ex=e)
        raise

def index_documents(documents_file: str) -> None:
    es = get_elasticsearch_client()
    documents = load_documents(documents_file)
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
    documents_file = "data/input/faqs/documents.json"
    index_documents(documents_file)
