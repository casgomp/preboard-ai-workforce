.PHONY: install dev test

install:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	cd frontend && npm ci

dev:
	.venv/bin/python scripts/dev.py

test:
	.venv/bin/python -m pytest
	cd frontend && npm test && npm run typecheck && npm run lint && npm run build
