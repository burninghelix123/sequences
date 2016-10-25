.PHONY: clean-pyc clean-build docs clean

# If the first argument is "run"...
ifeq (test,$(firstword $(MAKECMDGOALS)))
	# use the rest as arguments for "run"
	RUN_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
	# ...and turn them into do-nothing targets
	$(eval $(RUN_ARGS):;@:)
endif

uname_S := None
ifdef MSVC	# Avoid the MingW/Cygwin sections
	uname_S := Windows
else	# If uname not available => 'not'
	uname_S := $(shell sh -c 'uname -s 2>/dev/null || echo not')
endif

FIND := find
BROWSER := open
ifeq ($(OS),Windows_NT)
	BROWSER := cygstart
	FIND := /bin/find
else
	BROWSER := open
	FIND := find
endif


help:
	@echo "Primary"
	@echo "clean - Remove all build, test, coverage and Python artifacts"
	@echo "lint - Check style with flake8"
	@echo "test - Run tests"
	@echo "coverage - Run coverage on a dev machine with html in browser"
	@echo "docs - Generate Sphinx HTML documentation, including API docs"
	@echo "release - Package and upload a release"
	@echo "dev - Install in development mode which symlinks the source directory"
	@echo "install - Install the package to the active Python"
	@echo "uninstall - Uninstall the package if installed in the current Python"

	@echo "Advanced"
	@echo "clean-build - Remove build artifacts"
	@echo "clean-pyc - Remove Python file artifacts"
	@echo "clean-test - Remove test and coverage artifacts"
	@echo "clean-python-develop - Remove the development version installed with make dev"
	@echo "coverage-ci - Run coverage on the during gitlab ci"
	@echo "release-docs - Package and upload a release of docs"
	@echo "dist - Package"

clean: clean-build clean-pyc clean-test clean-python-develop clean-coverage

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	$(FIND) . -name '*.egg-info' -exec rm -fr {} +
	$(FIND) . -name '*.egg' -exec rm -f {} +

clean-pyc:
	$(FIND) . -name '*.pyc' -exec rm -f {} +
	$(FIND) . -name '*.pyo' -exec rm -f {} +
	$(FIND) . -name '*~' -exec rm -f {} +
	$(FIND) . -name '__pycache__' -exec rm -fr {} +

clean-test:
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/

clean-python-develop:
	python setup.py develop --uninstall

clean-coverage:
	$(FIND) . -name '*.coverage.*' -exec rm -fr {} +

lint:
	flake8 src/sequences tests

test:
	python setup.py test $(RUN_ARGS)

coverage_base:
	coverage run --source sequences setup.py test
	coverage combine

coverage: coverage_base
	coverage report -m
	coverage html
	$(BROWSER) htmlcov/index.html

coverage-ci: coverage_base
	coverage report -m | grep 'TOTAL' | egrep -o "[0-9\.]+\%"  | awk '{ print "covered " $$1;}'

dev: clean
	python setup.py develop

install: clean
	python setup.py install

uninstall:
	pip uninstall -y sequences

dist: clean
	python setup.py sdist

release: clean
	# Publish to pypi sever here:
	# echo "[distutils]" > ~/.pypirc
	# echo "index-servers = server-name" >> ~/.pypirc
	# echo "" >> ~/.pypirc
	# echo "[server-name]" >> ~/.pypirc
	# echo "repository: pypi server" >> ~/.pypirc
	# echo "username: user" >> ~/.pypirc
	# echo "password: password" >> ~/.pypirc
	# python setup.py sdist upload -r server-name

_docs:
	rm -f docs/sequences.rst
	rm -f docs/modules.rst
	sphinx-apidoc -d 10 -o docs/ src/sequences
	$(MAKE) -C docs clean
	$(MAKE) -C docs html

docs: _docs
	$(BROWSER) docs/_build/html/index.html

release-docs: _docs
	mv docs/_build/html docs/_build/sequences
	# Copy to ftp server here:
	# lftp -e "set ftp:list-options -a; rm -r sequences; mirror -R docs/_build/sequences ./; quit" ftp://user:pass@server