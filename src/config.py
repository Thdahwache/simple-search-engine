import os
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class ElasticsearchConfig:
    """Configuration settings for Elasticsearch connection and indexing"""
    host: str = "http://localhost:9200"
    index_name: str = "course-questions"
    search_boost: int = 3  # Boost factor for question field
    max_search_results: int = 5
    
    # Elasticsearch index settings
    index_settings: Dict[str, Any] = None
    
    def __post_init__(self):
        self.index_settings = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0
            },
            "mappings": {
                "properties": {
                    "text": {"type": "text"},
                    "section": {"type": "text"},
                    "question": {"type": "text"},
                    "course": {"type": "keyword"} 
                }
            }
        }

@dataclass
class OpenAIConfig:
    """Configuration settings for OpenAI API"""
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 10000

@dataclass
class AppConfig:
    """Configuration settings for the web application"""
    available_courses: List[str] = None
    
    def __post_init__(self):
        self.available_courses = [
            "data-engineering-zoomcamp",
            "machine-learning-zoomcamp",
            "mlops-zoomcamp"
        ] 