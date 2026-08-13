# RecipeAI — local app + kind/Argo sample
#
#   make help
#   make sync              # install uv (if needed) + deps
#   make test
#   make run               # local cuisine sample
#   make keys              # create/load OPENAI_API_KEY (.env)
#   make recipe-sample     # keys → kind/Argo setup → build → deploy → submit

.PHONY: help uv sync install test run run-cuisine run-ingredient \
	keys build setup setup-cluster deploy submit recipe-sample clean

ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
HACK := $(ROOT)/hack/run-workflow.sh
ENSURE_KEY := $(ROOT)/hack/ensure-openai-key.sh
UV ?= uv
export PATH := /opt/homebrew/bin:/usr/local/bin:$(HOME)/.local/bin:$(PATH)

# Local CLI sample defaults (override: make run CUISINE=thai)
MODE ?= cuisine
CUISINE ?= italian
MAX_PREP_TIME ?= 30
DIETARY_NEEDS ?=
REQUEST ?= chicken, spinach, garlic
NUTRITION_GOALS ?= high protein

# Kind sample workflow params (passed through to hack/run-workflow.sh)
KIND_MODE ?= cuisine
KIND_CUISINE ?= italian
KIND_MAX_PREP_TIME ?= 30
KIND_DIETARY_NEEDS ?=
KIND_REQUEST ?=
KIND_NUTRITION_GOALS ?=

help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nTargets:\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  %-18s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@printf "\nExamples:\n"
	@printf "  make sync && make test\n"
	@printf "  make keys && make run\n"
	@printf "  make recipe-sample\n"
	@printf "  make recipe-sample KIND_MODE=ingredient KIND_REQUEST='eggs and spinach'\n\n"

# --- toolchain / deps -------------------------------------------------------

uv: ## Install uv if missing
	@command -v $(UV) >/dev/null 2>&1 || { \
		echo "==> installing uv"; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	}
	@command -v $(UV) >/dev/null 2>&1 || { \
		echo "error: uv not on PATH after install; open a new shell or add \$$HOME/.local/bin" >&2; \
		exit 1; \
	}
	@$(UV) --version

sync: uv ## Create .venv and install project + dev deps
	$(UV) sync --extra dev

install: sync ## Alias for sync

# --- local app --------------------------------------------------------------

keys: ## Create or load OPENAI_API_KEY (prompts and writes .env if needed)
	@chmod +x $(ENSURE_KEY)
	@$(ENSURE_KEY)

test: sync ## Run pytest
	$(UV) run pytest -q

run: run-cuisine ## Alias for local cuisine sample

run-cuisine: sync keys ## Local cuisine-mode sample
	@set -a; [ -f $(ROOT)/.env ] && . $(ROOT)/.env; set +a; \
	$(UV) run main.py --mode cuisine --cuisine $(CUISINE) --max-prep-time $(MAX_PREP_TIME) \
		$(if $(DIETARY_NEEDS),--dietary-needs "$(DIETARY_NEEDS)",)

run-ingredient: sync keys ## Local ingredient-mode sample
	@set -a; [ -f $(ROOT)/.env ] && . $(ROOT)/.env; set +a; \
	$(UV) run main.py --mode ingredient --request "$(REQUEST)" \
		$(if $(NUTRITION_GOALS),--nutrition-goals "$(NUTRITION_GOALS)",)

# --- containers / kind ------------------------------------------------------

setup: ## Install podman/kind/argo and stand up kind + Argo + MinIO
	@chmod +x $(HACK)
	$(HACK) setup

setup-cluster: setup ## Alias for setup

build: ## Build container images with podman and load into kind
	@chmod +x $(HACK)
	$(HACK) build

deploy: keys ## Deploy MCP server + OpenAI secret into kind
	@chmod +x $(HACK) $(ENSURE_KEY)
	@set -a; [ -f $(ROOT)/.env ] && . $(ROOT)/.env; set +a; \
	$(HACK) deploy

submit: ## Submit the Argo workflow sample
	@chmod +x $(HACK)
	$(HACK) submit \
		--mode $(KIND_MODE) \
		--cuisine $(KIND_CUISINE) \
		--max-prep-time $(KIND_MAX_PREP_TIME) \
		$(if $(KIND_DIETARY_NEEDS),--dietary-needs "$(KIND_DIETARY_NEEDS)",) \
		$(if $(KIND_REQUEST),--request "$(KIND_REQUEST)",) \
		$(if $(KIND_NUTRITION_GOALS),--nutrition-goals "$(KIND_NUTRITION_GOALS)",)

recipe-sample: ## Full kind sample: keys → setup → build → deploy → submit
	@chmod +x $(HACK) $(ENSURE_KEY)
	@$(ENSURE_KEY)
	@set -a; [ -f $(ROOT)/.env ] && . $(ROOT)/.env; set +a; \
	$(HACK) all \
		--mode $(KIND_MODE) \
		--cuisine $(KIND_CUISINE) \
		--max-prep-time $(KIND_MAX_PREP_TIME) \
		$(if $(KIND_DIETARY_NEEDS),--dietary-needs "$(KIND_DIETARY_NEEDS)",) \
		$(if $(KIND_REQUEST),--request "$(KIND_REQUEST)",) \
		$(if $(KIND_NUTRITION_GOALS),--nutrition-goals "$(KIND_NUTRITION_GOALS)",)

clean: ## Remove local .venv (does not delete kind cluster or .env)
	rm -rf $(ROOT)/.venv
