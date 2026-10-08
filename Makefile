# Build, run and clean the retained LeRTX desktop application.
#
# This wraps desktop/manage.py, the project's canonical entry point (see
# desktop/README.md). It does not reimplement setup, packaging or test
# logic. Requires Linux x86-64/ARM64 or Windows 11 with an NVIDIA RTX GPU
# and driver, plus Python 3.11 or `uv` (see desktop/README.md for details).

ifeq ($(OS),Windows_NT)
PYTHON  ?= python
RUN := powershell -NoProfile -ExecutionPolicy Bypass -File "./run.ps1"
else
PYTHON  ?= python3
RUN = $(MANAGE) run
ifeq ($(shell uname -s),Darwin)
RUN := printf '%s\n' 'LeRTX cannot render on macOS: the pinned NVIDIA SDKs require Linux or Windows with an NVIDIA GPU.' >&2; exit 2
endif
endif
MANAGE  := $(PYTHON) desktop/manage.py

VENV_PYTHON := .venv/bin/python
ifeq ($(OS),Windows_NT)
VENV_PYTHON := .venv/Scripts/python.exe
endif

.PHONY: help build run test doctor install uninstall package rebuild clean

help:
	@echo "make build      create the isolated .venv and install pinned SDK dependencies"
	@echo "make run        launch the desktop application (builds first if needed)"
	@echo "make test       run the desktop application test suite"
	@echo "make doctor     report environment/runtime diagnostics"
	@echo "make install    add LeRTX to the desktop/Start Menu application launcher"
	@echo "make uninstall  remove the launcher created by 'make install'"
	@echo "make package    build dist/LeRTX-prototype.zip"
	@echo "make rebuild    clean, then build from scratch"
	@echo "make clean      remove .venv, dist/ and cached Python bytecode"

build: $(VENV_PYTHON)

# desktop/manage.py setup creates .venv on first run and installs the pinned,
# hash-checked SDK dependencies for this platform; it is safe to re-run.
$(VENV_PYTHON): desktop/manage.py desktop/source/requirements.txt
	$(MANAGE) setup
	@touch "$@"

# manage.py run owns setup freshness and failure recovery. In particular, this
# target must not inherit build's Unix-only touch recipe on Windows.
run:
	$(RUN)

test: build
	$(MANAGE) test

doctor: build
	$(MANAGE) doctor

install: build
	$(MANAGE) install

uninstall:
	$(MANAGE) uninstall

package:
	$(MANAGE) package

rebuild: clean
	$(MAKE) build

# Leaves any launcher installed by 'make install' in place; use 'make uninstall'
# for that. Does not touch _build/ or generated/, which are shared with the
# Literate AI harness rather than being desktop-app-specific build output.
clean:
	rm -rf .venv dist
	find desktop/source -type d -name "__pycache__" -exec rm -rf {} +
	find desktop/source -type f -name "*.py[co]" -delete
