# Installation Guide

This guide will help you set up the Simple Search Engine project on your system.

## Prerequisites

- Python 3.11 or higher
- pip (Python package installer)
- Elasticsearch 8.x
- Git (for version control)

## Step-by-Step Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/simple-search-engine
cd simple-search-engine
```

### 2. Set Up Python Environment

```bash
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

### 3. Install Dependencies

```bash
# Install the package with development dependencies
pip install -e ".[dev]"

# If you want to build documentation
pip install -e ".[docs]"
```

### 4. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your settings
# Required variables:
# - ELASTICSEARCH_URL
# - OPENAI_API_KEY (if using OpenAI embeddings)
```

### 5. Verify Installation

```bash
# Start the web interface
streamlit run src/web/app.py
```

## Common Issues

### Elasticsearch Connection

If you have issues connecting to Elasticsearch:

1. Ensure Elasticsearch is running
2. Check your ELASTICSEARCH_URL in .env
3. Verify Elasticsearch version compatibility

### Package Installation Issues

If you encounter package installation issues:

1. Ensure you're using Python 3.11+
2. Update pip: `pip install --upgrade pip`
3. Install build dependencies: `pip install wheel setuptools`

## Next Steps

- Follow the [Quick Start Guide](quickstart.md) to begin using the search engine
- Read about [Configuration Options](configuration.md)
- Explore the [API Reference](../api/core.md) 