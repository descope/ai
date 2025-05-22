VENV_DIR := .venv
PYTHON := $(VENV_DIR)/bin/python
PIP := $(VENV_DIR)/bin/pip

ifeq ($(OS),Windows_NT)
    PYTHON := $(VENV_DIR)/Scripts/python.exe
    PIP := $(VENV_DIR)/Scripts/pip.exe
endif

all: run

$(VENV_DIR):
	python3 -m venv $(VENV_DIR)

install: $(VENV_DIR)
	$(PIP) install -r requirements.txt

run: install
	$(PYTHON) server.py

clean:
	rm -rf $(VENV_DIR)
