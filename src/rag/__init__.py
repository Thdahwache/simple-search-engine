"""RAG (Retrieval-Augmented Generation) package."""

from .qa_bot import QABot
from .templates import CONTEXT_TEMPLATE, PROMPT_TEMPLATE

__all__ = ["QABot", "CONTEXT_TEMPLATE", "PROMPT_TEMPLATE"] 