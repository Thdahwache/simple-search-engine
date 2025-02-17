from typing import Any

from src.core.config import ElasticsearchConfig
from src.models.embedding import embed_text


def build_text_search_query(query: str, course: str | None = None) -> dict[str, Any]:
    """Build a traditional text-based search query."""
    should_conditions = [
        {
            "match": {
                "text": {
                    "query": query,
                    "boost": ElasticsearchConfig.search_boost
                }
            }
        },
        {"match": {"question": {"query": query}}}
    ]
    
    if course:
        filter_conditions = [{"term": {"course": course}}]
    else:
        filter_conditions = []

    return {
        "size": ElasticsearchConfig.max_search_results,
        "query": {
            "bool": {
                "should": should_conditions,
                "filter": filter_conditions,
                "minimum_should_match": 1
            }
        }
    }

def build_vector_search_query(query: str, course: str | None = None) -> dict[str, Any]:
    """Build a vector-based semantic search query."""
    query_vector = embed_text(query)
    
    if course:
        filter_conditions = [{"term": {"course": course}}]
    else:
        filter_conditions = []

    return {
        "size": ElasticsearchConfig.max_search_results,
        "query": {
            "bool": {
                "must": [{
                    "script_score": {
                        "query": {"match_all": {}},
                        "script": {
                            "source": "cosineSimilarity(params.query_vector, 'text_vector') + 1.0",
                            "params": {"query_vector": query_vector}
                        }
                    }
                }],
                "filter": filter_conditions
            }
        }
    }
