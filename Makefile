# Nothing that must stay private may be tracked: no compiled program (it carries the folder
# names of the machine it was built on), no file over 1 MiB, no name of a private machine,
# account or place. The ignore rules help; this check is what stops a mistake.
.PHONY: tracked-files
tracked-files:
	scripts/tracked-files.sh

# The change log page is not kept in this repository. It is built from the change log
# files of the server, the client and the packages, and the pages are checked with it in
# place, because the other pages link to it.
.PHONY: changelog
changelog:
	scripts/build-changelog.sh

check: tracked-files changelog
	python3 scripts/check.py

lint:
	shellcheck scripts/*.sh

publish: check
	scripts/publish.sh

.PHONY: check lint publish
