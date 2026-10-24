.PHONY: help install lint format test test-agents run-agents docker-up docker-down clean frontend-install frontend-dev backend-dev

help:
	@echo "GitPulse Multi-Agent & Data Engineering Platform CLI"
	@echo "======================================================"
	@echo "Available commands:"
	@echo "  make install         Install Python dependencies in editable mode"
	@echo "  make lint            Run ruff, black check, and mypy"
	@echo "  make format          Auto-format Python code with ruff and black"
	@echo "  make test            Run all pytest test suites (runtime + backend)"
	@echo "  make test-agents     Run multi-agent runtime test suite"
	@echo "  make run-agents      Execute Master Orchestrator task execution"
	@echo "  make docker-up       Start infrastructure containers via Docker Compose"
	@echo "  make docker-down     Stop and remove Docker Compose containers"
	@echo "  make frontend-install Install frontend npm dependencies"
	@echo "  make frontend-dev    Start Vite development server"
	@echo "  make backend-dev     Start FastAPI backend server with hot reload"
	@echo "  make clean           Clean caches, logs, and build artifacts"

install:
	python -m pip install --upgrade pip
	pip install -e ".[dev,streaming,storage]"

lint:
	ruff check agent_runtime backend
	black --check agent_runtime backend
	mypy agent_runtime backend

format:
	ruff check --fix agent_runtime backend
	black agent_runtime backend

test:
	pytest agent_runtime/tests backend/tests -v

test-agents:
	pytest agent_runtime/tests -v

run-agents:
	python -m agent_runtime.main run --task "Process initial repository backlog"

docker-up:
	docker compose up -d kafka minio redis prometheus grafana

docker-down:
	docker compose down

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

backend-dev:
	uvicorn backend.src.gitpulse.api.main:app --host 0.0.0.0 --port 8000 --reload

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf build dist .coverage htmlcov
