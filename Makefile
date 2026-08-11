PIP ?= python -m pip
PYTHON ?= python
RUFF ?= $(PYTHON) -m ruff

setup:
	$(PIP) install --upgrade pip
	$(PIP) install ruff

lint:
	$(RUFF) check src

format:
	$(RUFF) format src

check:
	$(MAKE) lint
	$(MAKE) format
