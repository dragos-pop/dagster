.PHONY: help

define GET_MAKEFILE_DIR
$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))) | sed 's:/*$$::')
endef

MAKEFILE_DIR := $(GET_MAKEFILE_DIR)
export TUTORIAL_EXAMPLE_DIR := $(MAKEFILE_DIR)
export DAGSTER_HOME := $(MAKEFILE_DIR)/.dagster_home
export AIRFLOW_HOME := $(MAKEFILE_DIR)/.airflow_home
export TUTORIAL_DBT_PROJECT_DIR := $(MAKEFILE_DIR)/tutorial_example/shared/dbt
export DBT_PROFILES_DIR := $(MAKEFILE_DIR)/tutorial_example/shared/dbt
export DAGSTER_URL := http://localhost:3000

# Detect OS and use appropriate date command
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
    TOMORROW_DATE := $(shell date -v+1d +"%Y-%m-%d")
else
    TOMORROW_DATE := $(shell date -d "+1 day" +"%Y-%m-%d")
endif

help:
	@egrep -h '\s##\s' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'


### TUTORIAL COMMANDS ###
wipe: ## Wipe out all the files created by the Makefile
	rm -rf $$AIRFLOW_HOME $$DAGSTER_HOME


airflow_install:
	pip install uv && \
	uv pip install dagster-airlift[in-airflow,tutorial] && \
	uv pip install -e $(MAKEFILE_DIR)

airflow_setup:
	make wipe && \
	mkdir -p $$AIRFLOW_HOME && \
	mkdir -p $$DAGSTER_HOME && \
	chmod +x $(MAKEFILE_DIR)/scripts/airflow_setup.sh && \
	$(MAKEFILE_DIR)/scripts/airflow_setup.sh $(MAKEFILE_DIR)/tutorial_example/airflow_dags && \
	dbt seed --project-dir $(TUTORIAL_DBT_PROJECT_DIR)

airflow_run:
	airflow standalone


dagster_run:
	dagster dev -m tutorial_example.dagster_defs.definitions -p 3000

backfill_today:
	airflow dags backfill rebuild_customers_list --start-date $(shell date +"%Y-%m-%d")

clean:
	airflow db clean --yes --clean-before-timestamp $(TOMORROW_DATE)
	dagster asset wipe --all --noprompt





update_readme_snippets:
	python ../../scripts/update_readme_snippets.py $(MAKEFILE_DIR)/README.md

