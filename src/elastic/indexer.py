import json
from tqdm.auto import tqdm
from elasticsearch import Elasticsearch
from ..config import ElasticsearchConfig
from ..utils.logger import setup_logger
from .client import get_elasticsearch_client
import os

logger = setup_logger(__name__)

print(os.getcwd())
def load_documents(file_path: str) -> list:
    with open(file_path, 'rt') as f_in:
        documents_file = json.load(f_in)

    documents = []
    for course in documents_file:
        course_name = course['course']
        for doc in course['documents']:
            doc['course'] = course_name
            documents.append(doc)
    
    print(documents)
    return documents

def create_index(es: Elasticsearch) -> None:
    try:
        es.indices.create(
            index=ElasticsearchConfig.index_name,
            body=ElasticsearchConfig.index_settings
        )
        logger.info(f"Created index: {ElasticsearchConfig.index_name}")
    except Exception as e:
        logger.error(f"Failed to create index: {e}")
        raise

def index_documents(documents_file: str) -> None:
    es = get_elasticsearch_client()
    documents = load_documents(documents_file)
    
    create_index(es)
    
    for doc in tqdm(documents):
        try:
            es.index(index=ElasticsearchConfig.index_name, document=doc)
        except Exception as e:
            logger.error(f"Failed to index document: {e}")
            continue

if __name__ == "__main__":
    documents_file = 'data/input/faqs/documents.json'
    index_documents(documents_file) 