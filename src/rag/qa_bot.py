from typing import Any

from openai import OpenAI

from ..core.config import ElasticsearchConfig, OpenAIConfig
from ..elastic.client import get_elasticsearch_client
from ..utils.logger import setup_logger
from .templates import CONTEXT_TEMPLATE, PROMPT_TEMPLATE

logger = setup_logger(__name__)


class QABot:
    """Question Answering bot that uses Elasticsearch for document retrieval
    and OpenAI for generating answers.
    """

    def __init__(self):
        self.elasticsearch_client = get_elasticsearch_client()
        self.openai_client = OpenAI()
        self.es_config = ElasticsearchConfig()
        self.openai_config = OpenAIConfig()

    def retrieve_documents(
        self, query: str, course: str, max_results: int = None
    ) -> list[dict[str, Any]]:
        """Retrieve relevant documents from Elasticsearch.

        Args:
            query: User's question
            course: Course identifier
            max_results: Maximum number of documents to retrieve

        Returns:
            List of relevant documents

        """
        max_results = max_results or self.es_config.max_search_results

        search_query = {
            "size": max_results,
            "query": {
                "bool": {
                    "must": {
                        "multi_match": {
                            "query": query,
                            "fields": [
                                f"question^{self.es_config.search_boost}",
                                "text",
                                "section",
                            ],
                            "type": "best_fields",
                        }
                    },
                    "filter": {
                        "term": {
                            "course.keyword": course
                        }
                    }
                }
            },
        }

        response = self.elasticsearch_client.search(
            index=self.es_config.index_name, body=search_query
        )
        return [hit["_source"] for hit in response["hits"]["hits"]]

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
        return PROMPT_TEMPLATE.format(
            user_question=user_question,
            context=context
        )

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
            error_msg = f"OpenAI API error: {e!s}"
            logger.error(error_msg)
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
                return "I couldn't find any relevant information to answer your question."

            prompt = self.build_prompt(user_question, context_docs)
            return self.ask_openai(prompt)
        except Exception as e:
            error_msg = f"Error in QA pipeline: {e!s}"
            logger.error(error_msg)
            return "I apologize, but something went wrong while processing your question. Please try again."
