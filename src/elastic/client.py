from elasticsearch import Elasticsearch

from ..core.config import ElasticsearchConfig
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


def get_elasticsearch_client() -> Elasticsearch:
    try:
        client = Elasticsearch(ElasticsearchConfig.host)
        logger.info("Successfully connected to Elasticsearch")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Elasticsearch: {e}")
        raise
