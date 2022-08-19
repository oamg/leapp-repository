# there are bashisms used in this Makefile
SHELL=/bin/bash

__PKGNAME=$${_PKGNAME:-leapp-repository}
VENVNAME ?= tut
DIST_VERSION ?= 7
PKGNAME=leapp-repository
DEPS_PKGNAME=leapp-el7toel8-deps
VERSION=`grep -m1 "^Version:" packaging/$(PKGNAME).spec | grep -om1 "[0-9].[0-9.]**"`
DEPS_VERSION=`grep -m1 "^Version:" packaging/$(DEPS_PKGNAME).spec | grep -om1 "[0-9].[0-9.]**"`
REPOS_PATH=repos
_SYSUPG_REPOS="$(REPOS_PATH)/system_upgrade"
LIBRARY_PATH=
REPORT_ARG=
REPOSITORIES ?= $(shell ls $(_SYSUPG_REPOS) | xargs echo | tr " " ",")
SYSUPG_TEST_PATHS=$(shell echo $(REPOSITORIES) | sed -r "s|(,\\|^)| $(_SYSUPG_REPOS)/|g")
TEST_PATHS:=commands repos/common $(SYSUPG_TEST_PATHS)


ifdef ACTOR
	TEST_PATHS=`python utils/actor_path.py $(ACTOR)`
endif

ifeq ($(TEST_LIBS),y)
	LIBRARY_PATH=`python utils/library_path.py`
endif

ifdef REPORT
	REPORT_ARG=--junit-xml=$(REPORT)
endif

# needed only in case the Python2 should be used
_USE_PYTHON_INTERPRETER=$${_PYTHON_INTERPRETER}

# python version to run test with
_PYTHON_VENV=$${PYTHON_VENV:-python2.7}

# by default use values you can see below, but in case the COPR_* var is defined
# use it instead of the default
_COPR_REPO=$${COPR_REPO:-leapp}
_COPR_REPO_TMP=$${COPR_REPO_TMP:-leapp-tmp}
_COPR_CONFIG=$${COPR_CONFIG:-~/.config/copr_rh_oamg.conf}

# tool used to run containers for testing and building packages
_CONTAINER_TOOL=$${CONTAINER_TOOL:-podman}

# container to run tests in
_TEST_CONTAINER=$${TEST_CONTAINER:-rhel8}

# In case just specific CHROOTs should be used for the COPR build, you can
# set the multiple CHROOTs separated by comma in the COPR_CHROOT envar, e.g.
# "epel-7-x86_64,epel-8-x86_64". But for the copr-cli utility, each of them
# has to be specified separately for the -r option; So we transform it
# automatically to "-r epel-7-x86_64 -r epel-8-x86_64" (without quotes).
ifdef COPR_CHROOT
	_COPR_CHROOT=`echo $${COPR_CHROOT} | grep -o "[^,]*" | sed "s/^/-r /g"`
endif

# just to reduce number of unwanted builds mark as the upstream one when
# someone will call copr_build without additional parameters
MASTER_BRANCH=master

# In case the PR or MR is defined or in case build is not comming from the
# MATER_BRANCH branch, N_REL=0; (so build is not update of the approved
# upstream solution). For upstream builds N_REL=100;
N_REL=`_NR=$${PR:+0}; if test "$${_NR:-100}" == "100"; then _NR=$${MR:+0}; fi; git rev-parse --abbrev-ref HEAD | grep -qE "^($(MASTER_BRANCH)|stable)$$" || _NR=0;  echo $${_NR:-100}`

TIMESTAMP:=$${__TIMESTAMP:-$(shell /bin/date -u "+%Y%m%d%H%MZ")}
SHORT_SHA=`git rev-parse --short HEAD`
BRANCH=`git rev-parse --abbrev-ref HEAD | tr -- '-/' '_'`

# The dependent framework PR connection will be taken from the top commit's depends-on message.
REQ_LEAPP_PR=$(shell git log master..HEAD | grep -m1 -iE '^[[:space:]]*Depends-On:[[:space:]]*.*[[:digit:]]+[[:space:]]*$$' | grep -Eo '*[[:digit:]]*')
# NOTE(ivasilev) In case of travis relying on top commit is a no go as a top commit will be a merge commit.
ifdef CI
	REQ_LEAPP_PR=$(shell git log master..HEAD | grep -m1 -iE '^[[:space:]]*Depends-On:[[:space:]]*.*[[:digit:]]+[[:space:]]*$$' | grep -Eo '[[:digit:]]*')
endif

# In case anyone would like to add any other suffix, just make it possible
_SUFFIX=`if test -n "$$SUFFIX"; then echo ".$${SUFFIX}"; fi; `

# generate empty string if PR or MR are not specified, otherwise set one of them
REQUEST=`if test -n "$$PR"; then echo ".PR$${PR}"; elif test -n "$$MR"; then echo ".MR$${MR}"; fi; `

# replace "custombuild" with some a describing your build
# Examples:
#    0.201810080027Z.4078402.packaging.PR2
#    0.201810080027Z.4078402.packaging
#    0.201810080027Z.4078402.master.MR2
#    1.201810080027Z.4078402.master
RELEASE="$(N_REL).$(TIMESTAMP).$(SHORT_SHA).$(BRANCH)$(REQUEST)$(_SUFFIX)"

all: help

help:
	@echo "Usage: make <target>"
	@echo
	@echo "Available targets are:"
	@echo "  help                        show this text"
	@echo "  clean                       clean the mess"
	@echo "  prepare                     clean the mess and prepare dirs"
	@echo "  print_release               print release how it should look like with"
	@echo "                              with the given parameters"
	@echo "  source                      create the source tarball suitable for"
	@echo "                              packaging"
	@echo "  srpm                        create the SRPM"
	@echo "  build_container             create the RPM in container"
	@echo "                              - set BUILD_CONTAINER to el7 or el8"
	@echo "                              - don't run more than one build at the same time"
	@echo "                                since containers operate on the same files!"
	@echo "  copr_build                  create the COPR build using the COPR TOKEN"
	@echo "                              - default path is: $(_COPR_CONFIG)"
	@echo "                              - can be changed by the COPR_CONFIG env"
	@echo "  install-deps                create python virtualenv and install there"
	@echo "                              leapp-repository with dependencies"
	@echo "  install-deps-fedora         create python virtualenv and install there"
	@echo "                              leapp-repository with dependencies for Fedora OS"
	@echo "  lint                        lint source code"
	@echo "  lint_fix                    attempt to fix isort violations inplace"
	@echo "  test                        lint source code and run tests"
	@echo "  test_no_lint                run tests without linting the source code"
	@echo "  test_container              run lint and tests in container"
	@echo "                              - default container is 'rhel8'"
	@echo "                              - can be changed by setting TEST_CONTAINER env"
	@echo "  test_container_all          run lint and tests in all available containers"
	@echo "  test_container_no_lint      run tests without linting in container, see test_container"
	@echo "  test_container_all_no_lint  run tests without linting in all available containers"
	@echo "  clean_containers            clean all testing and building container images (to force a rebuild for example)"
	@echo ""
	@echo "Targets test, lint and test_no_lint support environment variables ACTOR and"
	@echo "TEST_LIBS."
	@echo "If ACTOR=<actor> is specified, targets are run against the specified actor."
	@echo "If TEST_LIBS=y is specified, targets are run against shared libraries."
	@echo ""
	@echo "Envars affecting actions with COPR (optional):"
	@echo "  COPR_REPO             specify COPR repository, e,g. @oamg/leapp"
	@echo "                          (default: leapp)"
	@echo "  COPR_REPO_TMP         specify COPR repository for building of tmp"
	@echo "                        deps (meta) packages"
	@echo "                          (default: leapp-tmp)"
	@echo "  COPR_CONFIG           path to the COPR config with API token"
	@echo "                          (default: ~/.config/copr_rh_oamg.conf)"
	@echo "  COPR_CHROOT           specify the CHROOT which should be used for"
	@echo "                        the build, e.g. 'epel-7-x86_64'. You can"
	@echo "                        specify multiple CHROOTs separated by comma."
	@echo ""
	@echo "Possible use:"
	@echo "  make <target>"
	@echo "  PR=5 make <target>"
	@echo "  MR=6 make <target>"
	@echo "  PR=7 SUFFIX='my_additional_suffix' make <target>"
	@echo "  MR=6 COPR_CONFIG='path/to/the/config/copr/file' make <target>"
	@echo "  ACTOR=<actor> TEST_LIBS=y make test"
	@echo "  BUILD_CONTAINER=el7 make build_container"
	@echo "  TEST_CONTAINER=f34 make test_container"
	@echo "  CONTAINER_TOOL=docker TEST_CONTAINER=rhel7 make test_container_no_lint"
	@echo ""

clean:
	@echo "--- Clean repo ---"
	@rm -rf packaging/{sources,SRPMS,tmp,BUILD,BUILDROOT,RPMS}/
	@rm -rf build/ dist/ *.egg-info .pytest_cache/
	@rm -f *src.rpm packaging/*tar.gz
	@find . -name 'leapp.db' | grep "\.leapp/leapp.db" | xargs rm -f
	@find . -name '__pycache__' -exec rm -fr {} +
	@find . -name '*.pyc' -exec rm -f {} +
	@find . -name '*.pyo' -exec rm -f {} +

prepare: clean
	@echo "--- Prepare build directories ---"
	@mkdir -p packaging/{sources,SRPMS,BUILD,BUILDROOT,RPMS}/

source: prepare
	@echo "--- Create source tarball ---"
	@echo git archive --prefix "$(PKGNAME)-$(VERSION)/" -o "packaging/sources/$(PKGNAME)-$(VERSION).tar.gz" HEAD
	@git archive --prefix "$(PKGNAME)-$(VERSION)/" -o "packaging/sources/$(PKGNAME)-$(VERSION).tar.gz" HEAD
	@echo "--- PREPARE DEPS PKGS ---"
	mkdir -p packaging/tmp/
	@__TIMESTAMP=$(TIMESTAMP) $(MAKE) _build_subpkg
	@__TIMESTAMP=$(TIMESTAMP) $(MAKE) DIST_VERSION=$$(($(DIST_VERSION) + 1)) _build_subpkg
	@tar -czf packaging/sources/deps-pkgs.tar.gz -C packaging/RPMS/noarch `ls packaging/RPMS/noarch | grep -o "[^/]*rpm$$"`
	@rm -f packaging/RPMS/noarch/*.rpm

srpm: source
	@echo "--- Build SRPM: $(PKGNAME)-$(VERSION)-$(RELEASE).. ---"
	@cp packaging/$(PKGNAME).spec packaging/$(PKGNAME).spec.bak
	@sed -i "s/1%{?dist}/$(RELEASE)%{?dist}/g" packaging/$(PKGNAME).spec
	@rpmbuild -bs packaging/$(PKGNAME).spec \
		--define "_sourcedir `pwd`/packaging/sources"  \
		--define "_srcrpmdir `pwd`/packaging/SRPMS" \
		--define "rhel $(DIST_VERSION)" \
		--define 'dist .el$(DIST_VERSION)' \
		--define 'el$(DIST_VERSION) 1' || FAILED=1
	@mv packaging/$(PKGNAME).spec.bak packaging/$(PKGNAME).spec

_build_subpkg:
	@echo "--- Build RPM: $(DEPS_PKGNAME)-$(DEPS_VERSION)-$(RELEASE).. ---"
	@cp packaging/$(DEPS_PKGNAME).spec packaging/$(DEPS_PKGNAME).spec.bak
	@sed -i "s/1%{?dist}/$(RELEASE)%{?dist}/g" packaging/$(DEPS_PKGNAME).spec
	@rpmbuild -ba packaging/$(DEPS_PKGNAME).spec \
		--define "_sourcedir `pwd`/packaging/sources"  \
		--define "_srcrpmdir `pwd`/packaging/SRPMS" \
		--define "_builddir `pwd`/packaging/BUILD" \
		--define "_buildrootdir `pwd`/packaging/BUILDROOT" \
		--define "_rpmdir `pwd`/packaging/RPMS" \
		--define "rhel $$(($(DIST_VERSION) + 1))" \
		--define "dist .el$$(($(DIST_VERSION) + 1))" \
		--define "el$$(($(DIST_VERSION) + 1)) 1" || FAILED=1
	@mv packaging/$(DEPS_PKGNAME).spec.bak packaging/$(DEPS_PKGNAME).spec

_build_local: source
	@echo "--- Build RPM: $(PKGNAME)-$(VERSION)-$(RELEASE).. ---"
	@cp packaging/$(PKGNAME).spec packaging/$(PKGNAME).spec.bak
	@sed -i "s/1%{?dist}/$(RELEASE)%{?dist}/g" packaging/$(PKGNAME).spec
	@rpmbuild -ba packaging/$(PKGNAME).spec \
		--define "_sourcedir `pwd`/packaging/sources"  \
		--define "_srcrpmdir `pwd`/packaging/SRPMS" \
		--define "_builddir `pwd`/packaging/BUILD" \
		--define "_buildrootdir `pwd`/packaging/BUILDROOT" \
		--define "_rpmdir `pwd`/packaging/RPMS" \
		--define "rhel $(DIST_VERSION)" \
		--define "dist .el$(DIST_VERSION)" \
		--define "el$(DIST_VERSION) 1" || FAILED=1
	@mv packaging/$(PKGNAME).spec.bak packaging/$(PKGNAME).spec

build_container:
	echo "--- Build RPM ${PKGNAME}-${VERSION}-${RELEASE}.el$(DIST_VERSION).rpm in container ---"; \
	case "$(BUILD_CONTAINER)" in \
		el7) \
			CONT_FILE="utils/container-builds/Containerfile.centos7"; \
			;; \
		el8) \
			CONT_FILE="utils/container-builds/Containerfile.ubi8"; \
			;; \
		"") \
			echo "BUILD_CONTAINER must be set"; \
			exit 1; \
			;; \
		*) \
			echo "Available containers are el7, el8"; \
			exit 1; \
			;; \
	esac && \
	IMAGE="leapp-repo-build-$(BUILD_CONTAINER)"; \
	$(_CONTAINER_TOOL) image inspect $$IMAGE > /dev/null 2>&1 || \
	$(_CONTAINER_TOOL) build -f $$CONT_FILE --tag $$IMAGE . && \
	$(_CONTAINER_TOOL) run --rm --name "$${IMAGE}-cont" -v $$PWD:/repo:Z $$IMAGE

copr_build: srpm
	@echo "--- Build RPM ${PKGNAME}-${VERSION}-${RELEASE}.el$(DIST_VERSION).rpm in COPR ---"
	@echo copr-cli --config $(_COPR_CONFIG) build $(_COPR_CHROOT) $(_COPR_REPO) \
		packaging/SRPMS/${PKGNAME}-${VERSION}-${RELEASE}*.src.rpm
	@copr-cli --config $(_COPR_CONFIG) build $(_COPR_CHROOT) $(_COPR_REPO) \
		packaging/SRPMS/${PKGNAME}-${VERSION}-${RELEASE}*.src.rpm

print_release:
	@echo $(RELEASE)

# Before doing anything, it is good idea to register repos to ensure everything
# is in order inside ~/.config/leapp/repos.json
register:
	. $(VENVNAME)/bin/activate; \
	snactor repo find --path repos

install-deps:
	@# in centos:7 python 3.x is not installed by default
	case $(_PYTHON_VENV) in python3*) yum install -y ${shell echo $(_PYTHON_VENV) | tr -d .}; esac
	@# in centos:7 python dependencies required gcc
	case $(_PYTHON_VENV) in python3*) yum install gcc -y; esac
	virtualenv --system-site-packages -p /usr/bin/$(_PYTHON_VENV) $(VENVNAME); \
	. $(VENVNAME)/bin/activate; \
	pip install -U pip; \
	pip install --upgrade setuptools; \
	pip install --upgrade -r requirements.txt; \
	./utils/install_commands.sh $(_PYTHON_VENV); \
	# In case the top commit Depends-On some yet unmerged framework patch - override master leapp with the proper version
	if [[ ! -z "$(REQ_LEAPP_PR)" ]] ; then \
		echo "Leapp-repository depends on the yet unmerged pr of the framework #$(REQ_LEAPP_PR), installing it.." && \
		$(VENVNAME)/bin/pip install -I "git+https://github.com/oamg/leapp.git@refs/pull/$(REQ_LEAPP_PR)/head"; \
	fi
	$(_PYTHON_VENV) utils/install_actor_deps.py --actor=$(ACTOR) --repos="$(TEST_PATHS)"
install-deps-fedora:
	@# Check the necessary rpms are installed for py3 (and py2 below)
	if ! rpm -q git findutils python3-virtualenv gcc; then \
		if ! dnf install -y git findutils python3-virtualenv gcc; then \
			echo 'Please install the following rpms via the command: ' \
				'sudo dnf install -y git findutils python3-virtualenv gcc'; \
			exit 1; \
		fi; \
	fi
	@# Prepare the virtual environment
	virtualenv --system-site-packages --python /usr/bin/$(_PYTHON_VENV) $(VENVNAME)
	. $(VENVNAME)/bin/activate ; \
	pip install -U pip; \
	pip install --upgrade setuptools; \
	pip install --upgrade -r requirements.txt; \
	./utils/install_commands.sh $(_PYTHON_VENV); \
	# In case the top commit Depends-On some yet unmerged framework patch - override master leapp with the proper version
	if [[ ! -z "$(REQ_LEAPP_PR)" ]] ; then \
		echo "Leapp-repository depends on the yet unmerged pr of the framework #$(REQ_LEAPP_PR), installing it.." && \
		$(VENVNAME)/bin/pip install -I "git+https://github.com/oamg/leapp.git@refs/pull/$(REQ_LEAPP_PR)/head"; \
	fi

lint:
	. $(VENVNAME)/bin/activate; \
	echo "--- Linting ... ---" && \
	SEARCH_PATH="$(TEST_PATHS)" && \
	echo "Using search path '$${SEARCH_PATH}'" && \
	echo "--- Running pylint ---" && \
	bash -c "[[ ! -z '$${SEARCH_PATH}' ]] && find $${SEARCH_PATH} -name '*.py' | sort -u | xargs pylint -j0" && \
	echo "--- Running flake8 ---" && \
	bash -c "[[ ! -z '$${SEARCH_PATH}' ]] && flake8 $${SEARCH_PATH}"

	if [[ "$(_PYTHON_VENV)" == "python2.7" ]] ; then \
		. $(VENVNAME)/bin/activate; \
		echo "--- Checking py3 compatibility ---" && \
		SEARCH_PATH=$(REPOS_PATH) && \
		bash -c "[[ ! -z '$${SEARCH_PATH}' ]] && find $${SEARCH_PATH} -name '*.py' | sort -u | xargs pylint --py3k" && \
		echo "--- Linting done. ---"; \
	fi

	if [[  "`git rev-parse --abbrev-ref HEAD`" != "master" ]] && [[ -n "`git diff $(MASTER_BRANCH) --name-only`" ]]; then \
		. $(VENVNAME)/bin/activate; \
		git diff $(MASTER_BRANCH) --name-only | xargs isort -c --diff || \
		{ \
			echo; \
			echo "------------------------------------------------------------------------------"; \
			echo "Hint: Apply the required changes."; \
			echo "      Execute the following command to apply them automatically: make lint_fix"; \
			exit 1; \
		} && echo "--- isort check done. ---"; \
	fi

lint_fix:
	. $(VENVNAME)/bin/activate; \
	git diff $(MASTER_BRANCH) --name-only | xargs isort && \
	echo "--- isort inplace fixing done. ---;"

test_no_lint:
	. $(VENVNAME)/bin/activate; \
	snactor repo find --path repos/; \
	cd repos/system_upgrade/el7toel8/; \
	snactor workflow sanity-check ipu && \
	cd - && \
	$(_PYTHON_VENV) -m pytest $(REPORT_ARG) $(TEST_PATHS) $(LIBRARY_PATH)

test: lint test_no_lint

# container images act like a cache so that dependencies can only be downloaded once
# to force image rebuild, use clean_containers target
_build_container_image:
	@[ -z "$$CONT_FILE" ] && { echo "CONT_FILE must be set"; exit 1; } || \
	[ -z "$$TEST_IMAGE" ] && { echo "TEST_IMAGE must be set"; exit 1; }; \
	$(_CONTAINER_TOOL) image inspect "$$TEST_IMAGE" > /dev/null 2>&1 && exit 0; \
	echo "=========== Building container test env image ==========="; \
	$(_CONTAINER_TOOL) build -f $$CONT_FILE --tag $$TEST_IMAGE .

# tests one IPU, leapp repositories irrelevant to the tested IPU are deleted
_test_container_ipu:
	case $$TEST_CONT_IPU in \
	el7toel8) \
		export REPOSITORIES="common,el7toel8"; \
		;; \
	el8toel9) \
		export REPOSITORIES="common,el8toel9"; \
		;; \
	"") \
		echo "TEST_CONT_IPU must be set"; exit 1; \
		;; \
	*) \
		echo "Only supported TEST_CONT_IPUs are el7toel8, el8toel9"; exit 1; \
		;; \
	esac && \
	$(_CONTAINER_TOOL) exec -w /repocopy $$_CONT_NAME make clean && \
	$(_CONTAINER_TOOL) exec -w /repocopy -e REPOSITORIES $$_CONT_NAME make $${_TEST_CONT_TARGET:-test}

# Runs tests in a container
# Builds testing image first if it doesn't exist
# On some Python versions, we need to test both IPUs,
# because e.g. RHEL7 to RHEL8 IPU must work on python2.7 and python3.6
# and RHEL8 to RHEL9 IPU must work on python3.6 and python3.9.
test_container:
	case $(_TEST_CONTAINER) in \
	f34) \
		export CONT_FILE="utils/container-tests/Containerfile.f34"; \
		export _VENV="python3.9"; \
		;; \
	rhel7) \
		export CONT_FILE="utils/container-tests/Containerfile.rhel7"; \
		export _VENV="python2.7"; \
		;; \
	rhel8) \
		export CONT_FILE="utils/container-tests/Containerfile.rhel8"; \
		export _VENV="python3.6"; \
		;; \
	*) \
		echo "Error: Available containers are: f34, rhel7, rhel8"; exit 1; \
		;; \
	esac; \
	export TEST_IMAGE="leapp-repo-tests-$(_TEST_CONTAINER)"; \
	$(MAKE) _build_container_image && \
	echo "=========== Running tests in $(_TEST_CONTAINER) container ===============" && \
	export _CONT_NAME="leapp-repo-tests-$(_TEST_CONTAINER)-cont"; \
	$(_CONTAINER_TOOL) ps -q -f name=$$_CONT_NAME && { $(_CONTAINER_TOOL) kill $$_CONT_NAME; $(_CONTAINER_TOOL) rm $$_CONT_NAME; }; \
	$(_CONTAINER_TOOL) run -di --name $$_CONT_NAME -v "$$PWD":/repo:Z -e PYTHON_VENV=$$_VENV $$TEST_IMAGE && \
	$(_CONTAINER_TOOL) exec $$_CONT_NAME rsync -aur --delete --exclude "tut*" /repo/ /repocopy && \
	case $$_VENV in \
	python2.7) \
		TEST_CONT_IPU=el7toel8 $(MAKE) _test_container_ipu; \
		;;\
	python3.6) \
		TEST_CONT_IPU=el7toel8 $(MAKE) _test_container_ipu; \
		TEST_CONT_IPU=el8toel9 $(MAKE) _test_container_ipu; \
		;; \
	python3.9) \
		TEST_CONT_IPU=el8toel9 $(MAKE) _test_container_ipu; \
		;; \
	*) \
		TEST_CONT_IPU=el8toel9 $(MAKE) _test_container_ipu; \
		;;\
	esac; \
	$(_CONTAINER_TOOL) kill $$_CONT_NAME; \
	$(_CONTAINER_TOOL) rm $$_CONT_NAME

test_container_all:
	@for container in "f34" "rhel7" "rhel8"; do \
		TEST_CONTAINER=$$container $(MAKE) test_container || exit 1; \
	done

test_container_no_lint:
	@_TEST_CONT_TARGET="test_no_lint" $(MAKE) test_container

test_container_all_no_lint:
	@for container in "f34" "rhel7" "rhel8"; do \
		TEST_CONTAINER=$$container $(MAKE) test_container_no_lint || exit 1; \
	done

#TODO(mmatuska): Add lint_container and lint_container_all for running just lint in containers

# clean all testing and building containers and their images
clean_containers:
	for i in "leapp-repo-tests-f34" "leapp-repo-tests-rhel7" "leapp-repo-tests-rhel8" \
	"leapp-repo-build-el7" "leapp-repo-build-el8"; do \
		$(_CONTAINER_TOOL) kill "$$i-cont" || :; \
		$(_CONTAINER_TOOL) rm "$$i-cont" || :; \
		$(_CONTAINER_TOOL) rmi "$$i" || :;  \
	done > /dev/null 2>&1

fast_lint:
	@. $(VENVNAME)/bin/activate; \
	FILES_TO_LINT="$$(git diff --name-only $(MASTER_BRANCH)| grep '\.py$$')"; \
	if [[ -n "$$FILES_TO_LINT" ]]; then \
		pylint -j 0 $$FILES_TO_LINT && \
		flake8 $$FILES_TO_LINT; \
		LINT_EXIT_CODE="$$?"; \
		if [[ "$$LINT_EXIT_CODE" != "0" ]]; then \
			exit $$LINT_EXIT_CODE; \
		fi; \
		if [[ "$(_PYTHON_VENV)" == "python2.7" ]] ; then \
			pylint --py3k $$FILES_TO_LINT; \
		fi; \
	else \
		echo "No files to lint."; \
	fi

dashboard_data:
	. $(VENVNAME)/bin/activate; \
	snactor repo find --path repos/; \
	pushd repos/system_upgrade/el7toel8/; \
	$(_PYTHON_VENV) ../../../utils/dashboard-json-dump.py > ../../../discover.json; \
	popd

.PHONY: help build clean prepare source srpm copr_build _build_local build_container print_release register install-deps install-deps-fedora  lint test_no_lint test dashboard_data fast_lint
.PHONY: test_container test_container_no_lint test_container_all test_container_all_no_lint clean_containers _build_container_image _test_container_ipu
