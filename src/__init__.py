"""Simple Search Engine.

A search engine implementation using Elasticsearch and RAG techniques.
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from . import core
from . import elastic
from . import models
from . import rag
from . import utils
from . import web

__all__ = ["core", "elastic", "models", "rag", "utils", "web"] 