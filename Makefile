PIP ?= python -m pip
PYTHON ?= python
RUFF ?= $(PYTHON) -m ruff

setup:
	$(PIP) install --upgrade pip
	$(PIP) install ruff

lint:
	$(RUFF) check src lambda_function.py

format:
	$(RUFF) format src lambda_function.py

check:
	$(MAKE) lint
	$(MAKE) format
