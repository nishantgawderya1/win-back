.PHONY: install seed dev backend frontend test snapshot

install:
	cd backend && pip install -r requirements.txt --break-system-packages
	cd frontend && npm install

seed:
	python data/synthetic_batch.py --count 75 --output data/sample_batch.csv

backend:
	uvicorn backend.api.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

dev:
	@echo "Run 'make backend' and 'make frontend' in two terminals."

snapshot:
	python scripts/snapshot_demo_stats.py

test:
	pytest tests/ -v
