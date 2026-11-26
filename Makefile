.PHONY: start stop up down reset dev serve logs health

start: up
	@echo "Waiting for services..."
	@until curl -sf http://localhost:6333/healthz > /dev/null 2>&1; do printf '.'; sleep 2; done
	@until curl -sf http://localhost:7474 > /dev/null 2>&1; do printf '.'; sleep 2; done
	@echo " ready."
	$(MAKE) serve

stop:
	docker compose down

up:
	docker compose up -d

down:
	docker compose down

reset:
	docker compose down -v

dev:
	@lsof -ti:8000 | xargs kill -9 2>/dev/null || true
	PYTHONPATH=src uv run uvicorn versionrag.main:app --reload --reload-dir src --host 0.0.0.0 --port 8000

serve:
	@lsof -ti:8000 | xargs kill -9 2>/dev/null || true
	PYTHONPATH=src uv run uvicorn versionrag.main:app --host 0.0.0.0 --port 8000

logs:
	docker compose logs -f

health:
	curl -s localhost:8000/health | python3 -m json.tool
