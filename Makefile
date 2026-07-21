.PHONY: install test templates help

install:
	python -m pip install -e .

test:
	pytest

templates:
	grader --template-only

help:
	grader --help
