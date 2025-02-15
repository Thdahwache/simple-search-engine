# Makefile for DataTalks.Club Course Q&A System

.PHONY: all install install-uv run clean test lint elastic-docker elastic-health elastic-check index dev setup

# Default target
all: setup elastic-docker index run

# Setup environment and dependencies
setup: check-env install-uv

# Check and setup environment
check-env:
	@echo "Checking environment setup..."
	@if [ ! -f .env ]; then \
		if [ -f .env.example ]; then \
			echo "⚠️  .env file not found. Creating from .env.example..."; \
			cp .env.example .env; \
			echo "⚠️  Please edit .env file with your configurations."; \
			exit 1; \
		else \
			echo "❌ Neither .env nor .env.example files found!"; \
			exit 1; \
		fi \
	fi
	@if [ -z "$$OPENAI_API_KEY" ]; then \
		echo "❌ Error: OPENAI_API_KEY is not set in environment"; \
		echo "Please set it in your .env file or export it"; \
		exit 1; \
	fi
	@echo "✅ Environment check passed"

# Install dependencies with pip (default)
install:
	@echo "Installing dependencies with pip..."
	python -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt
	@echo "✅ Dependencies installed. Activate the virtual environment with:"
	@echo "source .venv/bin/activate  # Linux/Mac"
	@echo ".venv\\Scripts\\activate   # Windows"

# Install dependencies with uv (faster)
install-uv:
	@echo "Installing dependencies with uv..."
	@if ! command -v uv >/dev/null 2>&1; then \
		echo "UV not found. Installing UV..."; \
		sudo snap install astral-uv; \
	fi
	uv sync
	@echo "✅ Dependencies installed. Activate the virtual environment with:"
	@echo "source .venv/bin/activate  # Linux/Mac"
	@echo ".venv\\Scripts\\activate   # Windows"

# Start Elasticsearch with Docker
elastic-docker: elastic-stop
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
	@make elastic-health

# Basic Elasticsearch health check
elastic-health:
	@echo "Checking Elasticsearch health..."
	@# Check if Elasticsearch is running
	@if ! curl -s "http://localhost:9200/_cluster/health" >/dev/null; then \
		echo "❌ Elasticsearch is not running. Start it with:"; \
		echo "make elastic-docker"; \
		exit 1; \
	fi
	@echo "✅ Elasticsearch is running"
	
	@# Check cluster health
	@health=$$(curl -s "http://localhost:9200/_cluster/health" | grep -o '"status":"[^"]*"' | cut -d'"' -f4); \
	if [ "$$health" = "red" ]; then \
		echo "❌ Cluster health is red - there are serious issues"; \
		exit 1; \
	elif [ "$$health" = "yellow" ]; then \
		echo "⚠️  Cluster health is yellow - this is normal for single-node development clusters"; \
	else \
		echo "✅ Cluster health is green"; \
	fi

# Validate index status
elastic-check: elastic-health
	@echo "Validating Elasticsearch index..."
	@# Check indices
	@if ! curl -s "http://localhost:9200/_cat/indices?v" | grep -q "course-questions"; then \
		echo "❌ Index 'course-questions' does not exist"; \
		echo "Run 'make index' to create and populate the index"; \
		exit 1; \
	fi
	@echo "✅ Index 'course-questions' exists"
	
	@# Check document count
	@doc_count=$$(curl -s "http://localhost:9200/course-questions/_count" | grep -o '"count":[0-9]*' | cut -d':' -f2); \
	if [ "$$doc_count" -eq 0 ]; then \
		echo "❌ Index is empty (0 documents)"; \
		echo "Run 'make index' to populate the index"; \
		exit 1; \
	fi
	@echo "✅ Index contains $$doc_count documents"
	
	@# Check mapping
	@if ! curl -s "http://localhost:9200/course-questions/_mapping" | grep -q "keyword"; then \
		echo "⚠️  Warning: Index mapping might not be optimal - missing keyword fields"; \
	else \
		echo "✅ Index mapping includes keyword fields"; \
	fi
	
	@echo "\n✨ All Elasticsearch checks passed successfully!"

# Stop Elasticsearch Docker container
elastic-stop:
	@echo "Stopping Elasticsearch..."
	@if [ "$$(docker ps -q -f name=elasticsearch)" ]; then \
		docker stop elasticsearch; \
	else \
		echo "Elasticsearch is not running"; \
	fi

# Index documents
index: elastic-health
	@echo "Creating and indexing documents..."
	python -m src.elastic.indexer
	@make elastic-check

# Run the web application
run: elastic-check
	@echo "Starting Streamlit application..."
	python -m streamlit run src/web/app.py --server.port 8501 --server.address localhost --client.showSidebarNavigation false --server.headless true --server.fileWatcherType auto

# Development mode (with debug options)
dev: setup elastic-docker index
	@echo "Starting development server..."
	python -m streamlit run src/web/app.py --server.port 8501 --server.address localhost --server.runOnSave true --server.fileWatcherType auto

# Clean up the environment
clean: elastic-stop
	@echo "Cleaning up..."
	rm -rf venv .venv
	rm -rf **/__pycache__
	rm -rf .pytest_cache
	@echo "✅ Environment cleaned."