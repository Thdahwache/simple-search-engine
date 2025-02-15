"""Elasticsearch integration package."""

from .client import get_elasticsearch_client
from .indexer import create_index, index_documents, load_documents

__all__ = [
    "create_index",
    "get_elasticsearch_client",
    "index_documents",
    "load_documents",
]
