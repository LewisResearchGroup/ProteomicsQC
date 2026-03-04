ifeq ($(shell command -v docker-compose >/dev/null 2>&1 && echo yes),yes)
COMPOSE ?= docker-compose
else
COMPOSE ?= docker compose
endif

ifeq ($(shell id -u),0)
SUDO :=
else
SUDO ?= sudo
endif

PYTHON ?= /opt/conda/bin/python
RUN_WEB = $(SUDO) $(COMPOSE) run --rm web
RUN_WEB_LOCAL = $(SUDO) $(COMPOSE) -f docker-compose-develop.yml run --rm web

migrate: 
	$(RUN_WEB) $(PYTHON) manage.py migrate

migrations: 
	$(RUN_WEB) $(PYTHON) manage.py makemigrations $(ARGS)

migrate-local:
	$(RUN_WEB_LOCAL) $(PYTHON) manage.py migrate

migrations-local:
	$(RUN_WEB_LOCAL) $(PYTHON) manage.py makemigrations $(ARGS)

run:
	$(SUDO) $(COMPOSE) down && $(SUDO) $(COMPOSE) up

serve:
	$(SUDO) $(COMPOSE) -f docker-compose.yml down
	$(SUDO) $(COMPOSE) -f docker-compose.yml up -d
	@echo "Waiting for server on http://localhost:8080 ..."
	@until curl -sf http://localhost:8080/ >/dev/null; do \
		sleep 2; \
	done
	@echo "server is responding"
	@xdg-open http://localhost:8080 2>/dev/null || open http://localhost:8080 2>/dev/null || true
	@echo "Tailing web logs (Ctrl+C to stop logs; stack keeps running)..."
	$(SUDO) $(COMPOSE) -f docker-compose.yml logs -f web celery

devel:
	$(SUDO) $(COMPOSE) -f docker-compose-develop.yml down
	$(SUDO) $(COMPOSE) -f docker-compose-develop.yml up -d
	@echo "Waiting for dev server on http://127.0.0.1:8000 ..."
	@until curl -sf http://127.0.0.1:8000/ >/dev/null; do \
		sleep 2; \
	done
	@echo "server is responding"
	@xdg-open http://127.0.0.1:8000 2>/dev/null || open http://127.0.0.1:8000 2>/dev/null || true
	@echo "Tailing web logs (Ctrl+C to stop logs; stack keeps running)..."
	$(SUDO) $(COMPOSE) -f docker-compose-develop.yml logs -f web celery

devel-build:
	$(SUDO) $(COMPOSE) -f docker-compose-develop.yml down
	$(SUDO) $(COMPOSE) -f docker-compose-develop.yml up -d --build
	@echo "Waiting for dev server on http://127.0.0.1:8000 ..."
	@until curl -sf http://127.0.0.1:8000/ >/dev/null; do \
		sleep 2; \
	done
	@echo "server is responding"
	@xdg-open http://127.0.0.1:8000 2>/dev/null || open http://127.0.0.1:8000 2>/dev/null || true
	@echo "Tailing web logs (Ctrl+C to stop logs; stack keeps running)..."
	$(SUDO) $(COMPOSE) -f docker-compose-develop.yml logs -f web celery

build:
	$(SUDO) $(COMPOSE) build

build-local:
	$(SUDO) $(COMPOSE) -f docker-compose-develop.yml build

createsuperuser:
	$(RUN_WEB) $(PYTHON) manage.py createsuperuser

createsuperuser-local:
	$(RUN_WEB_LOCAL) $(PYTHON) manage.py createsuperuser

collectstatic:
	$(RUN_WEB) $(PYTHON) manage.py collectstatic --noinput

collectstatic-local:
	$(RUN_WEB_LOCAL) $(PYTHON) manage.py collectstatic --noinput

showenv:
	$(RUN_WEB) pip list

manage:
	$(RUN_WEB) $(PYTHON) manage.py $(CMD)

reset_migrations:
	sudo find . -path "*/migrations/*.pyc"  -delete
	sudo find . -path "*/migrations/*.py" -not -name "__init__.py" -delete

init:
	make build
	make migrations
	make migrations ARGS=user
	make migrations ARGS=maxquant
	make migrations ARGS=api
	make migrations ARGS=project
	make migrations ARGS=dashboards
	make migrate
	make createsuperuser
	make collectstatic
	make bootstrap-demo

init-local:
	make build-local
	make migrations-local
	make migrations-local ARGS=user
	make migrations-local ARGS=maxquant
	make migrations-local ARGS=api
	make migrations-local ARGS=project
	make migrations-local ARGS=dashboards
	make migrate-local
	make createsuperuser-local
	make collectstatic-local
	make bootstrap-demo-local

update:
	git pull --recurse-submodules
	make build
	make migrations
	make migrate

down:
	$(SUDO) $(COMPOSE) down
	$(SUDO) $(COMPOSE) -f docker-compose-develop.yml down

test: 
	$(SUDO) $(COMPOSE) -f docker-compose-test.yml run --rm web $(PYTHON) -m pytest

get-test-data:
	gdown --folder https://drive.google.com/drive/folders/1kdQUXbr6DTBNLFBXLYrR_RLoXDFwCh_N?usp=sharing --output app/tests/data/D01

doc:
	mkdocs gh-deploy

schema:
	$(SUDO) $(COMPOSE) -f docker-compose-develop.yml run --rm web $(PYTHON) manage.py graph_models --arrow-shape normal -o schema.png -a 

versions:
	$(SUDO) $(COMPOSE) run web conda env export -n base

bootstrap-demo:
	$(RUN_WEB) $(PYTHON) manage.py bootstrap_demo --user $${DEMO_USER:-user@email.com} --with-results

bootstrap-demo-local:
	$(RUN_WEB_LOCAL) $(PYTHON) manage.py bootstrap_demo --user $${DEMO_USER:-user@email.com} --with-results
