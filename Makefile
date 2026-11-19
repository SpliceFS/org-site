# Nothing that must stay private may be tracked: no compiled program (it carries the folder
# names of the machine it was built on), no file over 1 MiB, no name of a private machine,
# account or place. The ignore rules help; this check is what stops a mistake.
.PHONY: tracked-files
tracked-files:
	scripts/tracked-files.sh

# Every job of a workflow that runs on a runner has a time limit, so a hang fails in minutes
# and does not run for GitHub's default of 6 hours.
.PHONY: workflow-timeouts
workflow-timeouts:
	scripts/workflow-timeout-test.sh

# The finished pages: the pages of site/ with their part markers replaced by the files of
# parts/. Everything that is checked or published is in build/, never in site/.
.PHONY: build
build:
	python3 scripts/pages.py

# The change log page is not kept in this repository. It is built from the change log
# files of the server, the client and the packages into build/, and the pages are checked
# with it in place, because the other pages link to it. It needs build first, which replaces
# the whole build folder.
.PHONY: changelog
changelog: build
	scripts/build-changelog.sh

# The tests of the page builders. They use the files in tests/fixtures and need no network.
.PHONY: test
test:
	python3 -m unittest discover -s tests

check: tracked-files workflow-timeouts test build changelog
	python3 scripts/check.py

lint:
	shellcheck scripts/*.sh

publish: check
	scripts/publish.sh

.PHONY: check lint publish
