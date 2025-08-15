SDK_VERSION := 0.0

# -------------------------------------------------------------------------------------------------
# Development

clear:
	clear

clean: clear
	@rm -rf __pycache__ *.egg *.egg-info/ *.log
	@find . | grep -E "(/__pycache__$$|\.pyc$$|\.pyo$$)" | xargs rm -rf
	@rm -rf dist/*

prepare: clear
	python3 -m venv env

deps: clear
	env/bin/pip install --upgrade pip
	env/bin/pip install -r requirements.txt
	env/bin/pip install -r requirements-dev.txt

freeze: clear
	env/bin/pip freeze

shell: clear
	#source .env && PYTHONPATH="$$PYTHONPATH:."
	env/bin/python

format: clear
	env/bin/ruff format . --exclude sample_app

lint: clear clean format
	@# env/bin/pre-commit run --all-files
	env/bin/ruff check . --fix --exclude sample_app
	-env/bin/python -OO -m compileall --workers 10 -q apikit
	env/bin/mypy . --strict --exclude 'env/|tests|sample_app/'
	# --ignore-missing-imports

test:
	env/bin/pytest . -n auto

ci: clean format lint test

# -------------------------------------------------------------------------------------------------
# Library

lib: ci
	# 	clear ; env/bin/python setup.py build
	# 	clear ; env/bin/python setup.py sdist
	clear ; env/bin/python -m build
	clear ; env/bin/twine check dist/*

publish: lib
	# Fixing Python 3 Certificates
	# /Applications/Python\ 3.7/Install\ Certificates.command
	# Manual upload to PypI
	# http://pypi.python.org/pypi/THE-PROJECT
	# Go to 'edit' link
	# Update version and save
	# Go to 'files' link and upload the file
	clear ; env/bin/twine upload dist/* --username=UPDATE_ME --password=UPDATE_ME

# Git tasks

push: ci
	clear ; git push origin `git symbolic-ref --short HEAD`

tag:
	git tag ${SDK_VERSION}
	git push origin ${SDK_VERSION}

reset_tag:
	git tag -d ${SDK_VERSION}
	git push origin :refs/tags/${SDK_VERSION}
