from enum import Enum
from typing import Any

from openai import OpenAI

from src.core.config import ElasticsearchConfig, OpenAIConfig
from src.elastic.client import get_elasticsearch_client
from src.core.utils.logger import setup_logger
from src.rag.templates import CONTEXT_TEMPLATE, PROMPT_TEMPLATE
from src.elastic.queries import (
    build_text_search_query, 
    build_vector_search_query,
    build_question_vector_knn_query,
    build_text_vector_knn_query,
    build_question_text_vector_knn_query,
    build_combined_vector_knn_query
)

logger = setup_logger(__name__)


class SearchMethod(Enum):
    TEXT = "text"
    VECTOR = "vector"
    QUESTION_KNN = "question_knn"
    TEXT_KNN = "text_knn"
    QUESTION_TEXT_KNN = "question_text_knn"
    COMBINED_KNN = "combined_knn"


class QABot:
    """Question Answering bot that uses Elasticsearch for document retrieval
    and OpenAI for generating answers.
    """

    def __init__(self, search_method: SearchMethod = SearchMethod.TEXT) -> None:
        """Initialize the QA bot with required components."""
        self.search_method = search_method
        self.elasticsearch_client = get_elasticsearch_client()
        self.es_config = ElasticsearchConfig()
        self.openai_config = OpenAIConfig()
        self.openai_client = OpenAI(api_key=self.openai_config.open_api_key)

    def retrieve_documents(
        self, query: str, course: str, max_results: int | None = None
    ) -> list[dict[str, Any]]:
        """Retrieve relevant documents from Elasticsearch.

        Args:
            query: User's question
            course: Course identifier
            max_results: Maximum number of documents to retrieve

        Returns:
            List of relevant documents

        """
        if self.search_method == SearchMethod.TEXT:
            search_query = build_text_search_query(query, course)
        elif self.search_method == SearchMethod.VECTOR:
            search_query = build_vector_search_query(query, course)
        elif self.search_method == SearchMethod.QUESTION_KNN:
            search_query = build_question_vector_knn_query(query, course)
        elif self.search_method == SearchMethod.TEXT_KNN:
            search_query = build_text_vector_knn_query(query, course)
        elif self.search_method == SearchMethod.QUESTION_TEXT_KNN:
            search_query = build_question_text_vector_knn_query(query, course)
        elif self.search_method == SearchMethod.COMBINED_KNN:
            search_query = build_combined_vector_knn_query(query, course)
        else:
            logger.log_warning(f"Unknown search method: {self.search_method}. Falling back to text search.")
            search_query = build_text_search_query(query, course)

        try:
            response = self.elasticsearch_client.search(
                index=self.es_config.index_name, body=search_query
            )
            return [hit["_source"] for hit in response["hits"]["hits"]]
        except Exception as e:
            logger.log_error(f"Error retrieving documents using {self.search_method.value} search", ex=e)
            return []

    def build_context(self, documents: list[dict[str, Any]]) -> str:
        """Build context string from retrieved documents."""
        context_parts = []
        for doc in documents:
            doc_str = CONTEXT_TEMPLATE.format(**doc)
            context_parts.append(doc_str)

        return "\n\n".join(context_parts)

    def build_prompt(self, user_question: str, documents: list[dict[str, Any]]) -> str:
        """Build prompt for OpenAI using user question and retrieved documents."""
        context = self.build_context(documents)
        return PROMPT_TEMPLATE.format(user_question=user_question, context=context)

    def ask_openai(self, prompt: str) -> str:
        """Send prompt to OpenAI and get response.

        Args:
            prompt: Formatted prompt with context

        Returns:
            AI-generated answer

        """
        try:
            response = self.openai_client.chat.completions.create(
                model=self.openai_config.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.openai_config.temperature,
                max_tokens=self.openai_config.max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.log_error("OpenAI API error", ex=e)
            return "I apologize, but I encountered an error while processing your question. Please try again."

    def answer_question(self, user_question: str, course: str) -> str:
        """Main method to process user question and return answer.

        Args:
            user_question: User's question text
            course: Course identifier

        Returns:
            Answer to user's question

        """
        try:
            context_docs = self.retrieve_documents(user_question, course=course)
            if not context_docs:
                logger.log_warning(f"No relevant documents found for question: {user_question}")
                return "I couldn't find any relevant information to answer your question."

            prompt = self.build_prompt(user_question, context_docs)
            return self.ask_openai(prompt)
        except Exception as e:
            logger.log_error("Error in QA pipeline", ex=e)
            return "I apologize, but something went wrong while processing your question. Please try again."
