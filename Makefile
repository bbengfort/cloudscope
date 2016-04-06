# Shell to use with Make
SHELL := /bin/bash

# Set important Paths
PROJECT := cloudscope
LOCALPATH := $(CURDIR)/$(PROJECT)
PYTHONPATH := $(LOCALPATH)/
PYTHON_BIN := $(VIRTUAL_ENV)/bin

# Export targets not associated with files
.PHONY: test coverage pip virtualenv clean publish uml

# Clean build files
clean:
	find . -name "*.pyc" -print0 | xargs -0 rm -rf
	-rm -rf htmlcov
	-rm -rf .coverage
	-rm -rf build
	-rm -rf dist
	-rm -rf $(PROJECT).egg-info
	-rm -rf site
	-rm -rf classes_$(PROJECT).png
	-rm -rf packages_$(PROJECT).png

# Targets for testing
test:
	$(PYTHON_BIN)/nosetests -v --with-coverage --cover-package=$(PROJECT) --cover-inclusive --cover-erase tests

# Publish to gh-pages
publish:
	git subtree push --prefix=deploy origin gh-pages

# Draw UML diagrams
uml:
	pyreverse -ASmy -k -o png -p $(PROJECT) $(LOCALPATH)
