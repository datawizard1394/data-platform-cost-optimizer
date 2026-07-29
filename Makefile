.PHONY: help generate analyze demo compile test check lint clean

PYTHON ?= python3
SEED ?= 20260728

help:
	@echo "Synthetic Data Platform Cost Optimizer"
	@echo "  make demo      Generate and analyze a deterministic 60-day workload"
	@echo "  make check     Compile and run dependency-free tests"
	@echo "  make test      Run dependency-free tests"
	@echo "  make lint      Run ruff when installed"
	@echo "  make clean     Remove generated local artifacts"

generate:
	PYTHONPATH=src $(PYTHON) -m platform_cost.cli generate \
		--output data/input --seed $(SEED) --days 60 --workloads 12

analyze:
	PYTHONPATH=src $(PYTHON) -m platform_cost.cli analyze \
		--usage data/input/usage.csv \
		--billing data/input/billing.csv \
		--output reports

demo:
	PYTHONPATH=src $(PYTHON) -m platform_cost.cli demo \
		--workspace .demo --seed $(SEED) --days 60 --workloads 12

compile:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
		$(PYTHON) -m compileall -q src tests

test:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
		$(PYTHON) -m unittest discover -s tests -v

check: compile test

lint:
	$(PYTHON) -m ruff check src tests

clean:
	$(PYTHON) -c "import shutil; [shutil.rmtree(p, ignore_errors=True) for p in ('data/input', 'reports', '.demo', 'build', 'dist')]"
