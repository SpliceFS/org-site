# Nothing that must stay private may be tracked: no compiled program (it carries the folder
# names of the machine it was built on), no file over 1 MiB, no name of a private machine,
# account or place. The ignore rules help; this check is what stops a mistake.
.PHONY: tracked-files
tracked-files:
	scripts/tracked-files.sh

check: tracked-files
	python3 scripts/check.py

lint:
	shellcheck scripts/*.sh

publish: check
	scripts/publish.sh

.PHONY: check lint publish
