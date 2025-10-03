.PHONY: help install dev test lint format clean build deploy

# Default target
help:
	@echo "ReviewAssist Pro - Available Commands:"
	@echo ""
	@echo "  install     Install dependencies"
	@echo "  dev         Run development server"
	@echo "  test        Run tests"
	@echo "  lint        Run linting"
	@echo "  format      Format code"
	@echo "  clean       Clean build artifacts"
	@echo "  build       Build for production"
	@echo "  deploy      Deploy to production"
	@echo ""

# Install dependencies
install:
	python -m venv venv
	. venv/bin/activate && pip install --upgrade pip
	. venv/bin/activate && pip install -r requirements.txt
	. venv/bin/activate && pip install -r requirements-dev.txt

# Run development server
dev:
	. venv/bin/activate && python src/main.py

# Run tests
test:
	. venv/bin/activate && python -m pytest tests/ -v

# Run linting
lint:
	. venv/bin/activate && flake8 src/ tests/
	. venv/bin/activate && pylint src/

# Format code
format:
	. venv/bin/activate && black src/ tests/
	. venv/bin/activate && isort src/ tests/

# Clean build artifacts
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/

# Build for production
build: clean
	. venv/bin/activate && python setup.py sdist bdist_wheel

# Deploy to production (placeholder)
deploy:
	@echo "Deployment configuration needed"
	@echo "Configure your deployment target (Manus, DigitalOcean, etc.)"

