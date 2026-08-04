.DEFAULT_GOAL := help
PYTHON ?= python

.PHONY: help install build lint test-unit test-integration smoke check-services web worker scheduler validate
help:
	@printf '%s\n' 'install build lint test-unit test-integration smoke validate web worker scheduler check-services'
install:
	$(PYTHON) --version | grep -E 'Python 3\.12\.'
	node --version | grep -E '^v(20|22)\.'
	$(PYTHON) -m pip install -r requirements-dev.txt
	npm --prefix frontend ci
build:
	$(PYTHON) backend/manage.py check
	npm --prefix frontend run build
lint:
	$(PYTHON) -m ruff check backend tests
	NFX_PROFILE=test NFX_SECRET_KEY=synthetic-test-django-secret DATABASE_URL=postgresql://nfx_test:nfx_test_only@127.0.0.1:5432/nfx_test MINIO_ROOT_PASSWORD=nfx-test-only-password $(PYTHON) -m mypy backend
	npm --prefix frontend run lint
test-unit:
	NFX_PROFILE=test NFX_SECRET_KEY=synthetic-test-django-secret DATABASE_URL=postgresql://nfx_test:nfx_test_only@127.0.0.1:5432/nfx_test MINIO_ROOT_PASSWORD=nfx-test-only-password $(PYTHON) -m pytest tests/unit
test-integration:
	./scripts/test-integration.sh
smoke:
	./scripts/smoke.sh
check-services:
	$(PYTHON) backend/manage.py check_services
web:
	NFX_PROCESS=web $(PYTHON) backend/manage.py runserver 0.0.0.0:8000
worker:
	NFX_PROCESS=worker $(PYTHON) backend/manage.py worker
scheduler:
	NFX_PROCESS=scheduler $(PYTHON) backend/manage.py scheduler
validate: build lint test-unit test-integration smoke
