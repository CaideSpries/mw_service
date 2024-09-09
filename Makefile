# Makefile for setting up the virtual environment, installing packages, and running the app

# Define variables
VENV_DIR = venv
PYTHON = python3
PIP = $(VENV_DIR)/bin/pip
PYTHON_BIN = $(VENV_DIR)/bin/python

# Default target
all: setup run

# Create virtual environment
$(VENV_DIR):
	$(PYTHON) -m venv $(VENV_DIR)

# Install required packages
install: $(VENV_DIR)
	$(PIP) install -r requirements.txt

# Setup environment and install packages
setup: install

# Run the application
run:
	$(PYTHON_BIN) app.py

# Clean up the virtual environment
clean:
	rm -rf $(VENV_DIR)

rm_logs:
	rm -rf *.avi *.csv

.PHONY: all setup install run clean