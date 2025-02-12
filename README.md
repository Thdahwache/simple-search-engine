# DataTalks.Club Course Q&A System

A Question-Answering system built with RAG (Retrieval-Augmented Generation) for learning purposes, based on the LLM ZoomCamp Workshop by DataTalks.Club.

## Overview

This project implements a simple but effective Q&A system that helps students find answers to their questions about DataTalks.Club courses. It combines:

- **Elasticsearch** for efficient document retrieval
- **OpenAI's GPT model** for natural language understanding
- **Streamlit** for the web interface

## Features

- 🔍 **Semantic search** using Elasticsearch
- 🤖 **Context-aware answers** using OpenAI's LLM
- 🎯 **Course-specific question handling**
- 📱 **User-friendly web interface**
- 📝 **Detailed logging system**

## Architecture

RAG (Retrieval Augmented Generation) Flow:
User Question → Elasticsearch Retrieval → Context Building → OpenAI Processing → Answer

## Installation

To set up the project locally, follow these steps:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/course_qa_system.git
   cd course_qa_system
   ```

2. **Install dependencies:**
   You have two options for installing dependencies:

   Using traditional pip (default):
   ```bash
   make install
   ```

   Using UV (faster installation):
   ```bash
   make install-uv
   ```

3. **Set up Elasticsearch:**
   The project uses Docker to run Elasticsearch. Start it with:
   ```bash
   make elastic-docker
   ```

   Other Elasticsearch commands:
   - Check status: `make elastic-check`
   - Stop Elasticsearch: `make elastic-stop`

4. **Configure OpenAI API:**
   Sign up for an API key from OpenAI and set it in your environment variables:
   ```bash
   export OPENAI_API_KEY='your_api_key_here'
   ```
   Verify the API key is set:
   ```bash
   make check-env
   ```

## Usage

To run the web application:

```bash
make run
```

For development with auto-reload:
```bash
make dev
```

Open your web browser and navigate to `http://localhost:8501` to access the application.

## Development

The project includes several make commands to help with development:

```bash
make all              # Full setup: install dependencies, start Elasticsearch, and index documents
make index           # Index documents in Elasticsearch
make clean           # Clean up environment and stop Elasticsearch
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Thanks to DataTalks.Club for the educational resources and support.
- Special thanks to the contributors and the community for their valuable input.

## Contact

For any inquiries, please reach out to [your_email@example.com].