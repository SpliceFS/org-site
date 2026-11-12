check:
	python3 scripts/check.py

lint:
	shellcheck --shell=sh scripts/*.sh

publish: check
	scripts/publish.sh

.PHONY: check lint publish
