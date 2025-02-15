from elasticsearch import Elasticsearch

from src.core.config import ElasticsearchConfig
from src.core.utils.logger import setup_logger

logger = setup_logger(__name__)


def get_elasticsearch_client() -> Elasticsearch:
    try:
        client = Elasticsearch(ElasticsearchConfig.host)
        logger.log_info("Successfully connected to Elasticsearch")
        return client
    except Exception as e:
        logger.log_error("Failed to connect to Elasticsearch", ex=e)
        raise
