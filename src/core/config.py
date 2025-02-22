import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv

env_file = ".env"
load_dotenv(env_file, override=True)


@dataclass
class ElasticsearchConfig:
    """Configuration settings for Elasticsearch connection and indexing."""

    host: str = os.getenv("ELASTICSEARCH_HOST")
    index_name: str = os.getenv("ELASTICSEARCH_INDEX_NAME")
    search_boost: int = os.getenv("ELASTICSEARCH_SEARCH_BOOST")
    max_search_results: int = os.getenv("ELASTICSEARCH_MAX_SEARCH_RESULTS")
    embedding_dim: int = 768  # Dimension for all-mpnet-base-v2

    # Elasticsearch index settings
    index_settings: dict[str, Any] = None

    def __post_init__(self):
        self.index_settings = {
            "settings": {"number_of_shards": 1, "number_of_replicas": 0},
            "mappings": {
                "properties": {
                    "text": {"type": "text"},
                    "section": {"type": "text"},
                    "question": {"type": "text"},
                    "course": {"type": "keyword"},
                    "id": {"type": "keyword"},
                    "text_vector": {
                        "type": "dense_vector",
                        "dims": self.embedding_dim,
                        "index": True,
                        "similarity": "cosine"
                    },
                    "question_vector": {
                        "type": "dense_vector",
                        "dims": self.embedding_dim,
                        "index": True,
                        "similarity": "cosine"
                    },
                    "question_text_vector": {
                        "type": "dense_vector",
                        "dims": self.embedding_dim,
                        "index": True,
                        "similarity": "cosine"
                    }  
                }
            },
        }


@dataclass
class OpenAIConfig:
    """Configuration settings for OpenAI API."""

    open_api_key: str = os.getenv("OPENAI_API_KEY")
    model: str = os.getenv("OPENAI_MODEL")
    temperature: float = float(os.getenv("OPENAI_TEMPERATURE"))
    max_tokens: int = int(os.getenv("OPENAI_MAX_TOKENS"))