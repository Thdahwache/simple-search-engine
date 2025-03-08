# Simple Search Engine

A powerful search engine implementation using Elasticsearch and RAG (Retrieval-Augmented Generation) techniques.

## Features

- 🔍 Full-text search capabilities using Elasticsearch
- 🤖 RAG-based search enhancement
- 📊 Vector embeddings for semantic search
- 🌐 Web interface using Streamlit
- 🔄 Easy integration with existing systems

## Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/simple-search-engine
cd simple-search-engine

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run the web interface
streamlit run src/web/app.py
```

## Project Structure

```
simple-search-engine/
├── src/               # Source code
│   ├── core/         # Core functionality
│   ├── elastic/      # Elasticsearch integration
│   ├── models/       # ML models and embeddings
│   ├── rag/          # RAG implementation
│   ├── utils/        # Utility functions
│   └── web/          # Web interface
├── docs/             # Documentation
├── notebooks/        # Jupyter notebooks
└── data/            # Data directory
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the terms of the MIT license. 