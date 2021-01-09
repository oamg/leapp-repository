__PKGNAME=$${_PKGNAME:-leapp-repository}
VENVNAME ?= tut
PKGNAME=leapp-repository
DEPS_PKGNAME=leapp-el7toel8-deps
VERSION=`grep -m1 "^Version:" packaging/$(PKGNAME).spec | grep -om1 "[0-9].[0-9.]**"`
DEPS_VERSION=`grep -m1 "^Version:" packaging/$(DEPS_PKGNAME).spec | grep -om1 "[0-9].[0-9.]**"`
REPOS_PATH=repos
ACTOR_PATH=
LIBRARY_PATH=
REPORT_ARG=

ifdef ACTOR
	ACTOR_PATH=`python utils/actor_path.py $(ACTOR)`
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

# In some cases we want to build rpms just for specific chroot. Currently just
# one chroot is processed by makefile, but the copr utility is able to process
# multiple chroots (for each -r one chroot is allowed).
ifdef COPR_CHROOT
	_COPR_CHROOT=-r=$${COPR_CHROOT}
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
	@echo "  help                   show this text"
	@echo "  clean                  clean the mess"
	@echo "  prepare                clean the mess and prepare dirs"
	@echo "  print_release          print release how it should look like with"
	@echo "                         with the given parameters"
	@echo "  source                 create the source tarball suitable for"
	@echo "                         packaging"
	@echo "  srpm                   create the SRPM"
	@echo "  copr_build             create the COPR build using the COPR TOKEN"
	@echo "                         - default path is: $(_COPR_CONFIG)"
	@echo "                         - can be changed by the COPR_CONFIG env"
	@echo "  install-deps           create python virtualenv and install there"
	@echo "                         leapp-repository with dependencies"
	@echo "  install-deps-fedora    create python virtualenv and install there"
	@echo "                         leapp-repository with dependencies for Fedora OS"
	@echo "  lint                   lint source code"
	@echo "  test                   lint source code and run tests"
	@echo "  test_no_lint           run tests without linting the source code"
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
	@echo "                        the build, e.g. epel-7-x86_64"
	@echo ""
	@echo "Possible use:"
	@echo "  make <target>"
	@echo "  PR=5 make <target>"
	@echo "  MR=6 make <target>"
	@echo "  PR=7 SUFFIX='my_additional_suffix' make <target>"
	@echo "  MR=6 COPR_CONFIG='path/to/the/config/copr/file' make <target>"
	@echo "  ACTOR=<actor> TEST_LIBS=y make test"
	@echo ""

clean:
	@echo "--- Clean repo ---"
	@rm -rf packaging/{sources,SRPMS,tmp}/
	@rm -rf build/ dist/ *.egg-info .pytest_cache/
	@find . -name 'leapp.db' | grep "\.leapp/leapp.db" | xargs rm -f
	@find . -name '__pycache__' -exec rm -fr {} +
	@find . -name '*.pyc' -exec rm -f {} +
	@find . -name '*.pyo' -exec rm -f {} +

prepare: clean
	@echo "--- Prepare build directories ---"
	@mkdir -p packaging/{sources,SRPMS}/

source: prepare
	@echo "--- Create source tarball ---"
	@echo git archive --prefix "$(PKGNAME)-$(VERSION)/" -o "packaging/sources/$(PKGNAME)-$(VERSION).tar.gz" HEAD
	@git archive --prefix "$(PKGNAME)-$(VERSION)/" -o "packaging/sources/$(PKGNAME)-$(VERSION).tar.gz" HEAD
	@echo "--- PREPARE DEPS PKGS ---"
	mkdir -p packaging/tmp/
	@__TIMESTAMP=$(TIMESTAMP) $(MAKE) _copr_build_deps_subpkg
	@PKG_RELEASE=$(RELEASE) _COPR_CONFIG=$(_COPR_CONFIG) \
		COPR_REPO=$(_COPR_REPO_TMP) COPR_PACKAGE=$(DEPS_PKGNAME) \
		$(_USE_PYTHON_INTERPRETER) ./utils/get_latest_copr_build > packaging/tmp/deps_build_id
	@copr --config $(_COPR_CONFIG) download-build -d packaging/tmp `cat packaging/tmp/deps_build_id`
	# Move rpms from any subfolder of packaging/tmp/, like packaging/tmp/rhel-8.dev-x86_64/, to packaging/tmp/
	@mv `find packaging/tmp/ | grep "rpm$$" | grep -v "src"` packaging/tmp
	@tar -czf packaging/sources/deps-pkgs.tar.gz -C packaging/tmp/ `ls packaging/tmp | grep -o "[^/]*rpm$$"`
	@rm -rf packaging/tmp

srpm: source
	@echo "--- Build SRPM: $(PKGNAME)-$(VERSION)-$(RELEASE).. ---"
	@cp packaging/$(PKGNAME).spec packaging/$(PKGNAME).spec.bak
	@sed -i "s/1%{?dist}/$(RELEASE)%{?dist}/g" packaging/$(PKGNAME).spec
	@rpmbuild -bs packaging/$(PKGNAME).spec \
		--define "_sourcedir `pwd`/packaging/sources"  \
		--define "_srcrpmdir `pwd`/packaging/SRPMS" \
		--define "rhel 7" \
		--define 'dist .el7' \
		--define 'el7 1' || FAILED=1
	@mv packaging/$(PKGNAME).spec.bak packaging/$(PKGNAME).spec

_srpm_subpkg:
	@echo "--- Build RPM: $(DEPS_PKGNAME)-$(DEPS_VERSION)-$(RELEASE).. ---"
	@cp packaging/$(DEPS_PKGNAME).spec packaging/$(DEPS_PKGNAME).spec.bak
	@sed -i "s/1%{?dist}/$(RELEASE)%{?dist}/g" packaging/$(DEPS_PKGNAME).spec
	@rpmbuild -bs packaging/$(DEPS_PKGNAME).spec \
		--define "_sourcedir `pwd`/packaging/sources"  \
		--define "_srcrpmdir `pwd`/packaging/SRPMS" \
		--define "rhel 8" \
		--define 'dist .el8' \
		--define 'el7 8' || FAILED=1
	@mv packaging/$(DEPS_PKGNAME).spec.bak packaging/$(DEPS_PKGNAME).spec

_copr_build_deps_subpkg: _srpm_subpkg
	@echo "--- Build RPM ${DEPS_PKGNAME}-${DEPS_VERSION}-${RELEASE} in TMP CORP ---"
	@echo copr --config $(_COPR_CONFIG) build $(_COPR_CHROOT) $(_COPR_REPO_TMP) \
		packaging/SRPMS/${DEPS_PKGNAME}-${DEPS_VERSION}-${RELEASE}*.src.rpm
	@copr --config $(_COPR_CONFIG) build $(_COPR_CHROOT) $(_COPR_REPO_TMP) \
		packaging/SRPMS/${DEPS_PKGNAME}-${DEPS_VERSION}-${RELEASE}*.src.rpm


copr_build: srpm
	@echo "--- Build RPM ${PKGNAME}-${VERSION}-${RELEASE}.el6.rpm in COPR ---"
	@echo copr --config $(_COPR_CONFIG) build $(_COPR_CHROOT) $(_COPR_REPO) \
		packaging/SRPMS/${PKGNAME}-${VERSION}-${RELEASE}*.src.rpm
	@copr --config $(_COPR_CONFIG) build $(_COPR_CHROOT) $(_COPR_REPO) \
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
	@# in centos:7 actor's python 3.x dependencies are in epel
	case $(_PYTHON_VENV) in python3*) yum install -y epel-release; esac
	@# in centos:7 python dependencies required gcc
	case $(_PYTHON_VENV) in python3*) yum install gcc -y; esac
	virtualenv --system-site-packages -p /usr/bin/$(_PYTHON_VENV) $(VENVNAME); \
	. $(VENVNAME)/bin/activate; \
	pip install -U pip; \
	pip install --upgrade setuptools; \
	pip install --upgrade -r requirements.txt \
	# In case the top commit Depends-On some yet unmerged framework patch - override master leapp with the proper version
	if [[ ! -z "$(REQ_LEAPP_PR)" ]] ; then \
		echo "Leapp-repository depends on the yet unmerged pr of the framework #$(REQ_LEAPP_PR), installing it.." && \
		$(VENVNAME)/bin/pip install -I "git+https://github.com/oamg/leapp.git@refs/pull/$(REQ_LEAPP_PR)/head"; \
	fi
	python utils/install_actor_deps.py --actor=$(ACTOR)

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
	# In case the top commit Depends-On some yet unmerged framework patch - override master leapp with the proper version
	if [[ ! -z "$(REQ_LEAPP_PR)" ]] ; then \
		echo "Leapp-repository depends on the yet unmerged pr of the framework #$(REQ_LEAPP_PR), installing it.." && \
		$(VENVNAME)/bin/pip install -I "git+https://github.com/oamg/leapp.git@refs/pull/$(REQ_LEAPP_PR)/head"; \
	fi

lint:
	. $(VENVNAME)/bin/activate; \
	echo "--- Linting ... ---" && \
	SEARCH_PATH=$(REPOS_PATH) && \
	echo "Using search path '$${SEARCH_PATH}'" && \
	echo "--- Running pylint ---" && \
	bash -c "[[ ! -z $${SEARCH_PATH} ]] && find $${SEARCH_PATH} -name '*.py' | sort -u | xargs pylint" && \
	echo "--- Running flake8 ---" && \
	bash -c "[[ ! -z $${SEARCH_PATH} ]] && flake8 $${SEARCH_PATH}" && \
	echo "--- Checking py3 compatibility ---" && \
	bash -c "[[ ! -z $${SEARCH_PATH} ]] && find $${SEARCH_PATH} -name '*.py' | sort -u | xargs pylint --py3k" && \
	echo "--- Linting done. ---"

test_no_lint:
	. $(VENVNAME)/bin/activate; \
	snactor repo find --path repos/; \
	cd repos/system_upgrade/el7toel8/; \
	snactor workflow sanity-check ipu && \
	cd - && \
	python -m pytest $(REPORT_ARG) $(ACTOR_PATH) $(LIBRARY_PATH)

test: lint test_no_lint

dashboard_data:
	. $(VENVNAME)/bin/activate; \
	snactor repo find --path repos/; \
	pushd repos/system_upgrade/el7toel8/; \
	python ../../../utils/dashboard-json-dump.py > ../../../discover.json; \
	popd

.PHONY: help build clean prepare source srpm copr_build print_release register install-deps install-deps-fedora lint test_no_lint test dashboard_data
