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

def build_knn_query(query: str, field: str, course: str | None = None) -> dict[str, Any]:
    """Build a KNN vector search query for a specific vector field.
    
    Args:
        query: The search query text
        field: The vector field to search (e.g., 'question_vector', 'text_vector')
        course: Optional course filter
        
    Returns:
        Elasticsearch KNN query

    """
    query_vector = embed_text(query)

    knn = {
        "field": field,
        "query_vector": query_vector,
        "k": ElasticsearchConfig.max_search_results,
        "num_candidates": 10000,
    }

    # Add course filter if specified
    if course:
        knn["filter"] = {
            "term": {
                "course": course
            }
        }

    return {
        "knn": knn,
        "_source": ["id", "text", "section", "question", "course"]
    }

def build_question_vector_knn_query(query: str, course: str | None = None) -> dict[str, Any]:
    """Build a KNN search query using the question vector field.
    
    This searches for similar questions based on the question vector embedding.
    """
    return build_knn_query(query, "question_vector", course)

def build_text_vector_knn_query(query: str, course: str | None = None) -> dict[str, Any]:
    """Build a KNN search query using the text vector field.
    
    This searches for similar document content based on the text vector embedding.
    """
    return build_knn_query(query, "text_vector", course)

def build_question_text_vector_knn_query(query: str, course: str | None = None) -> dict[str, Any]:
    """Build a KNN search query using the combined question-text vector field.
    
    This searches using a vector that represents both the question and its answer text.
    """
    return build_knn_query(query, "question_text_vector", course)

def build_combined_vector_knn_query(query: str, course: str | None = None) -> dict[str, Any]:
    """Build a combined KNN query that uses all vector fields together.
    
    Uses script scoring to combine similarity scores from question, text, and 
    question_text vectors for more robust matching.
    """
    query_vector = embed_text(query)

    filter_condition = {"term": {"course": course}} if course else {"match_all": {}}

    return {
        "size": ElasticsearchConfig.max_search_results,
        "query": {
            "bool": {
                "must": [
                    {
                        "script_score": {
                            "query": filter_condition,
                            "script": {
                                "source": """
                                    cosineSimilarity(params.query_vector, 'question_vector') + 
                                    cosineSimilarity(params.query_vector, 'text_vector') + 
                                    cosineSimilarity(params.query_vector, 'question_text_vector') + 
                                    1.0
                                """,
                                "params": {
                                    "query_vector": query_vector
                                }
                            }
                        }
                    }
                ],
                "filter": {"term": {"course": course}} if course else []
            }
        },
        "_source": ["id", "text", "section", "question", "course"]
    }

def build_all_documents_query(size: int = 10000) -> dict[str, Any]:
    """Build a query to retrieve all documents.
    
    Args:
        size: Maximum number of documents to return. Default is 10000.
        
    Returns:
        Query to retrieve all documents with their required fields.

    """
    return {
        "size": size,
        "query": {
            "match_all": {}
        },
        "_source": ["id", "text", "section", "question", "course"]
    }
