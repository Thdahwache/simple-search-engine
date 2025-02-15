import json
from typing import Any

from elasticsearch import Elasticsearch
from tqdm.auto import tqdm

from ..core.config import ElasticsearchConfig
from ..utils.logger import setup_logger
from .client import get_elasticsearch_client

logger = setup_logger(__name__)


def load_documents(file_path: str) -> list[dict[str, Any]]:
    with open(file_path) as f_in:
        documents_file = json.load(f_in)

    documents = []
    for course in documents_file:
        course_name = course["course"]
        for doc in course["documents"]:
            doc["course"] = course_name
            documents.append(doc)

    return documents


def create_index(es: Elasticsearch) -> None:
    try:
        es.indices.create(
            index=ElasticsearchConfig.index_name, body=ElasticsearchConfig.index_settings
        )
        logger.info("Created index: %s", ElasticsearchConfig.index_name)
    except Exception as e:
        logger.error("Failed to create index %s: %s", ElasticsearchConfig.index_name, str(e), exc_info=True)
        raise


def index_documents(documents_file: str) -> None:
    es = get_elasticsearch_client()
    documents = load_documents(documents_file)

    create_index(es)

    for doc in tqdm(documents):
        try:
            es.index(index=ElasticsearchConfig.index_name, document=doc)
        except Exception as e:
            logger.error("Failed to index document: %s", str(e), exc_info=True)
            raise


if __name__ == "__main__":
    documents_file = "data/input/faqs/documents.json"
    index_documents(documents_file)
