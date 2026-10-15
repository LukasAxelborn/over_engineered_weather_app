# =============================================================================
# Weather platform — task runner (docker compose v2 / v5).
# Run `make help` for a summary.
# =============================================================================

COMPOSE ?= docker compose
PROJECT ?= weather
URL     ?= https://weather.local

.DEFAULT_GOAL := help
.PHONY: help env certs build up down restart ps logs clean clean-all \
        up-obs up-ops up-all build-all backup health tls-inspect pull

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

env: ## Create .env from .env.example (does not overwrite)
	@test -f .env || cp .env.example .env && echo ".env ready (edit the passwords!)"

certs: ## Generate local CA + leaf cert + dashboard auth file
	sh proxy/gen-certs.sh

build: ## Build the core images (web, api)
	$(COMPOSE) build

build-all: ## Build every image across all profiles
	$(COMPOSE) --profile observability --profile ops --profile queue \
	  --profile analytics --profile errors --profile storage build

up: env ## Start the CORE tier (traefik, web, api, redis, postgres, worker)
	$(COMPOSE) up -d

up-obs: env ## Start core + observability
	$(COMPOSE) --profile observability up -d

up-ops: env ## Start core + ops (portainer, adminer, ofelia, backups, watchtower)
	$(COMPOSE) --profile ops up -d

up-all: env ## Start everything
	$(COMPOSE) --profile observability --profile ops --profile queue \
	  --profile analytics --profile errors --profile storage up -d

down: ## Stop and remove containers (keeps data volumes)
	$(COMPOSE) --profile observability --profile ops --profile queue \
	  --profile analytics --profile errors --profile storage down

restart: ## Restart the core tier
	$(COMPOSE) restart

ps: ## Show running containers
	$(COMPOSE) --profile observability --profile ops --profile queue \
	  --profile analytics --profile errors --profile storage ps

logs: ## Tail core logs
	$(COMPOSE) logs -f --tail=200

logs-obs: ## Tail observability logs
	$(COMPOSE) --profile observability logs -f --tail=200

pull: ## Pull all base images
	$(COMPOSE) --profile observability --profile ops --profile queue \
	  --profile analytics --profile errors --profile storage pull

health: ## Check the API health endpoint over TLS
	curl -fsS $(URL)/api/health | python3 -m json.tool

tls-inspect: ## Inspect the served certificate SANs
	@echo | openssl s_client -connect localhost:443 -servername weather.local 2>/dev/null \
	  | openssl x509 -noout -text | grep -A1 "Subject Alternative Name" || true

backup: ## Run a one-off DB backup (ops profile)
	$(COMPOSE) --profile ops exec backup /backup/backup.sh

clean: down ## Stop core + remove containers

clean-all: ## Stop and DELETE all data volumes (destructive!)
	$(COMPOSE) --profile observability --profile ops --profile queue \
	  --profile analytics --profile errors --profile storage down -v
