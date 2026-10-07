.PHONY: dev up test lint bench bench-holdout bench-score injection

dev: ## run the whole stack in the foreground
	docker compose up --build

up: ## run the stack in the background
	docker compose up -d --build

test: ## all tests
	cd backend && uv run pytest

lint: ## ruff (with security rules), format check, TypeScript type check
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && pnpm build

bench: ## benchmark, dev set, all three setups on free Flash Lite; re-run to resume after the daily cap
	cd backend && PYTHONPATH=.. uv run python -m benchmark.runner bench --split dev

bench-holdout: ## holdout set, once at the end (never for tuning); MODEL=gemini-3.8-flash for the bonus run
	cd backend && PYTHONPATH=.. uv run python -m benchmark.runner bench --split holdout $(if $(MODEL),--model $(MODEL))

bench-score: ## score a results file and write the tables into the docs: make bench-score FILE=benchmark/results/x.jsonl
	cd backend && PYTHONPATH=.. uv run python -m benchmark.score ../$(FILE) --write

injection: ## live prompt-injection suite on the free Flash Lite model (~40 requests)
	cd backend && PYTHONPATH=.. uv run python -m benchmark.runner injection
