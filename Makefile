.PHONY: install dev dev-python dev-frontend test test-python test-frontend ingest deploy

PYTHON := python3
# Must match frontend/.env's PYTHON_API_URL. Override if 8000 is taken locally:
# make dev PORT=8010 (and set PYTHON_API_URL=http://localhost:8010 in frontend/.env).
PORT ?= 8000

install:
	$(PYTHON) -m pip install -r requirements.txt
	cd frontend && npm install

## Run the Python brain and the frontend together; Ctrl-C stops both.
# No .ONESHELL: here on purpose — macOS ships GNU Make 3.81, which predates
# .ONESHELL (added in 3.82) and silently runs each recipe line in its own throwaway
# shell instead, breaking the trap/background/wait below. Backslash continuations
# keep the whole thing one shell invocation on every Make version.
dev:
	trap 'kill 0' EXIT INT TERM; \
	( set -a; . .env; set +a; $(PYTHON) -m uvicorn server:app --reload --port $(PORT) ) & \
	( cd frontend && npm run dev ) & \
	wait

dev-python:
	set -a; . .env; set +a; $(PYTHON) -m uvicorn server:app --reload --port $(PORT)

dev-frontend:
	cd frontend && npm run dev

test: test-python test-frontend

test-python:
	$(PYTHON) -m pytest

test-frontend:
	cd frontend && npm test && npm run typecheck && npm run lint

## Re-ingest data/*.md into Unity Catalog (document_chunks/company_documents).
ingest:
	set -a; . .env; set +a; $(PYTHON) -m preboard.uc_corpus

## Deploy the Streamlit fallback app to Databricks Apps.
deploy:
	databricks bundle deploy
	databricks bundle run preboard
