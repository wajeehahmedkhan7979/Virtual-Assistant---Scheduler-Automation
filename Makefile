.PHONY: help install dev build up down logs clean test lint format docker-clean

help:
	@echo "VA Scheduler - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install dependencies"
	@echo "  make dev              Run development environment (Docker)"
	@echo ""
	@echo "Docker:"
	@echo "  make build            Build Docker images"
	@echo "  make up               Start Docker containers"
	@echo "  make down             Stop Docker containers"
	@echo "  make logs             Show container logs"
	@echo "  make docker-clean     Clean Docker resources"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test             Run pytest"
	@echo "  make lint             Run pylint/flake8"
	@echo "  make format           Format code with black"
	@echo ""
	@echo "Database:"
	@echo "  make db-migrate       Run database migrations (placeholder)"
	@echo "  make db-seed          Seed database with sample data (placeholder)"
	@echo ""

install:
	python -m venv venv
	. venv/Scripts/activate && pip install --upgrade pip setuptools
	. venv/Scripts/activate && pip install -r requirements.txt

dev: build up
	@echo "VA Scheduler is running at http://localhost:8000"
	@echo "FastAPI docs: http://localhost:8000/docs"

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

test:
	pytest tests/ -v --cov=backend

lint:
	pylint backend/ --disable=all --enable=E,F

format:
	black backend/ tests/

db-migrate:
	@echo "Database migrations placeholder"

db-seed:
	@echo "Database seed placeholder"

docker-clean:
	docker-compose down -v
	docker system prune -f

.DEFAULT_GOAL := help
