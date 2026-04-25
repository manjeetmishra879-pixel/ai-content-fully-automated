# Makefile for common development tasks

.PHONY: help install dev-install lint format test coverage clean build docs serve docker-build docker-up docker-down

help:
	@echo "AI Content Platform - Development Tasks"
	@echo ""
	@echo "Available commands:"
	@echo "  make install          Install dependencies"
	@echo "  make dev-install      Install with dev dependencies"
	@echo "  make lint             Run linters (flake8, mypy)"
	@echo "  make format           Format code (black, isort)"
	@echo "  make test             Run tests"
	@echo "  make coverage         Generate coverage report"
	@echo "  make clean            Clean build artifacts"
	@echo "  make docker-build     Build Docker images"
	@echo "  make docker-up        Start Docker Compose services"
	@echo "  make docker-down      Stop Docker Compose services"
	@echo "  make docs             Build documentation"

install:
	pip install -r requirements.txt

dev-install:
	pip install -r requirements.txt
	pip install pytest pytest-cov black isort flake8 mypy sphinx

lint:
	flake8 app worker
	mypy app worker --ignore-missing-imports

format:
	black app worker
	isort app worker

test:
	pytest tests/ -v

coverage:
	pytest tests/ --cov=app --cov=worker --cov-report=html
	@echo "Coverage report: htmlcov/index.html"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov build dist *.egg-info

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docs:
	cd docs && make html
	@echo "Docs: docs/_build/html/index.html"
