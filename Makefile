# Makefile for DataTalks.Club Course Q&A System

.PHONY: all install install-uv run clean test lint elastic-docker elastic-check index dev

# Default target
all: install elastic-docker index

# Install dependencies with pip (default)
install:
	@echo "Installing dependencies with pip..."
	python -m venv venv
	. venv/bin/activate && pip install -r requirements.txt
	@echo "Dependencies installed. Activate the virtual environment with:"
	@echo "source venv/bin/activate  # Linux/Mac"
	@echo "venv\\Scripts\\activate   # Windows"

# Install dependencies with uv (faster)
install-uv:
	@echo "Installing dependencies with uv..."
	@if ! command -v uv >/dev/null 2>&1; then \
		echo "UV not found. Installing UV..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	fi
	uv sync
	@echo "Dependencies installed. Activate the virtual environment with:"
	@echo "source .venv/bin/activate  # Linux/Mac"
	@echo ".venv\Scripts\activate   # Windows"

# Start Elasticsearch with Docker
elastic-docker:
	@echo "Starting Elasticsearch with Docker..."
	@if [ "$$(docker ps -q -f name=elasticsearch)" ]; then \
		echo "Elasticsearch is already running"; \
	else \
		docker run -d \
			--rm \
			--name elasticsearch \
			-m 2G \
			-p 9200:9200 \
			-p 9300:9300 \
			-e "discovery.type=single-node" \
			-e "xpack.security.enabled=false" \
			docker.elastic.co/elasticsearch/elasticsearch:8.4.3; \
		echo "Waiting for Elasticsearch to start..."; \
		sleep 30; \
	fi

# Check Elasticsearch status
elastic-check:
	@echo "Checking Elasticsearch status..."
	@if curl -s "http://localhost:9200/_cluster/health" >/dev/null; then \
		echo "Elasticsearch is running"; \
	else \
		echo "Elasticsearch is not running. Start it with:"; \
		echo "make elastic-docker"; \
		exit 1; \
	fi

# Stop Elasticsearch Docker container
elastic-stop:
	@echo "Stopping Elasticsearch..."
	@if [ "$$(docker ps -q -f name=elasticsearch)" ]; then \
		docker stop elasticsearch; \
	else \
		echo "Elasticsearch is not running"; \
	fi

# Check elasticsearch indexs
elastic-check-index:
	@echo "Checking Elasticsearch indexes..."
	@if [ "$$(curl -s "http://localhost:9200/_cat/indices?h=index" | grep -q "course-questions")" ]; then \
		echo "Elasticsearch index 'course-questions' exists"; \
	else \
		echo "Elasticsearch index 'course-questions' does not exist"; \
		exit 1; \
	fi

# Index documents
index: elastic-check
	@echo "Indexing documents..."
	python -m src.elastic.indexer

# Run the web application
run: elastic-check
	@echo "Starting Streamlit application..."
	python -m streamlit run src/web/app.py --server.port 8501 --server.address localhost --client.showSidebarNavigation false --server.headless true --server.fileWatcherType auto


# Clean up the environment
clean: elastic-stop
	@echo "Cleaning up..."
	rm -rf venv
	rm -rf __pycache__
	rm -rf .pytest_cache
	@echo "Environment cleaned."

# Check environment variables
check-env:
	@if [ -z "$$OPENAI_API_KEY" ]; then \
		echo "Error: OPENAI_API_KEY is not set"; \
		exit 1; \
	fi