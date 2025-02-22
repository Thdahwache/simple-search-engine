from elasticsearch import Elasticsearch

from src.core.config import ElasticsearchConfig
from src.core.utils.logger import setup_logger

logger = setup_logger(__name__)


def get_elasticsearch_client() -> Elasticsearch:
    """Create and return a configured Elasticsearch client.

    This function creates a new Elasticsearch client using the host configuration
    from ElasticsearchConfig. It verifies the connection and logs the status.

    Returns:
        Elasticsearch: A configured Elasticsearch client instance.

    Raises:
        Exception: If connection to Elasticsearch fails.
    """
    try:
        client = Elasticsearch(ElasticsearchConfig.host)
        logger.log_info("Successfully connected to Elasticsearch")
        return client
    except Exception as e:
        logger.log_error("Failed to connect to Elasticsearch", ex=e)
        raise
