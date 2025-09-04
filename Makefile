.PHONY: test test-cov test-fast lint clean install dev-install run

# Переменные
PYTHON := python3
PIP := $(PYTHON) -m pip
TEST_DIR := tests/
SRC_DIR := .
COVERAGE_DIR := htmlcov/

# Цели
help: ## Показать эту справку
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Установить зависимости
	$(PIP) install -r requirements.txt

dev-install: ## Установить зависимости для разработки (включая тесты)
	$(PIP) install -r requirements.txt
	$(PIP) install pytest pytest-asyncio pytest-mock pytest-cov black flake8 mypy

test: ## Запустить все тесты
	$(PYTHON) -m pytest $(TEST_DIR) -v

test-cov: ## Запустить тесты с покрытием кода
	$(PYTHON) -m pytest $(TEST_DIR) --cov=$(SRC_DIR) --cov-report=html --cov-report=term-missing

test-fast: ## Запустить тесты без покрытия (быстро)
	$(PYTHON) -m pytest $(TEST_DIR) --tb=short

test-unit: ## Запустить только unit тесты
	$(PYTHON) -m pytest $(TEST_DIR) -k "not integration" -v

test-integration: ## Запустить только интеграционные тесты
	$(PYTHON) -m pytest $(TEST_DIR) -k "integration" -v

lint: ## Проверить код линтером
	$(PYTHON) -m flake8 $(SRC_DIR) --max-line-length=120 --extend-ignore=E203,W503
	$(PYTHON) -m black --check --diff $(SRC_DIR)

format: ## Форматировать код
	$(PYTHON) -m black $(SRC_DIR)

type-check: ## Проверить типы
	$(PYTHON) -m mypy $(SRC_DIR) --ignore-missing-imports

clean: ## Очистить кэш и временные файлы
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -delete
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -name "dashboard_*.png" -type f -delete
	rm -rf .coverage

clean-cache: ## Очистить кэш GPX файлов
	find cache/ -name "*.gpx" -type f -delete

run: ## Запустить бота
	$(PYTHON) bot.py

run-dev: ## Запустить бота в режиме разработки
	$(PYTHON) -m bot

# Цели для CI/CD
ci: lint type-check test-cov ## Запустить полный CI пайплайн

# Показать покрытие в браузере (после test-cov)
coverage-show:
	@if [ -d "$(COVERAGE_DIR)" ]; then \
		open $(COVERAGE_DIR)/index.html; \
	else \
		echo "Сначала запустите 'make test-cov'"; \
	fi