.PHONY: dev up test lint bench

dev: ## run the whole stack in the foreground
	docker compose up --build

up: ## run the stack in the background
	docker compose up -d --build

test: ## all tests
	cd backend && uv run pytest

lint: ## ruff (with security rules), format check, TypeScript type check
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && pnpm build

bench: ## benchmark runner (built in Phase 4)
	@echo "The benchmark runner is built in Phase 4 (docs/PLAN.md)." && exit 1
