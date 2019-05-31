__PKGNAME=$${_PKGNAME:-leapp-repository}
PKGNAME=leapp-repository
DEPS_PKGNAME=leapp-el7toel8-deps
VERSION=`grep -m1 "^Version:" packaging/$(PKGNAME).spec | grep -om1 "[0-9].[0-9.]**"`
DEPS_VERSION=`grep -m1 "^Version:" packaging/$(DEPS_PKGNAME).spec | grep -om1 "[0-9].[0-9.]**"`

# needed only in case the Python2 should be used
_USE_PYTHON_INTERPRETER=$${_PYTHON_INTERPRETER}

# by default use values you can see below, but in case the COPR_* var is defined
# use it instead of the default
_COPR_REPO=$${COPR_REPO:-leapp}
_COPR_REPO_TMP=$${COPR_REPO_TMP:-leapp-tmp}
_COPR_CONFIG=$${COPR_CONFIG:-~/.config/copr_rh_oamg.conf}

# just to reduce number of unwanted builds mark as the upstream one when
# someone will call copr_build without additional parameters
MASTER_BRANCH=master

# In case the PR or MR is defined or in case build is not comming from the
# MATER_BRANCH branch, N_REL=0; (so build is not update of the approved
# upstream solution). For upstream builds N_REL=1;
N_REL=`_NR=$${PR:+0}; if test "$${_NR:-1}" == "1"; then _NR=$${MR:+0}; fi; git rev-parse --abbrev-ref HEAD | grep -qE "^($(MASTER_BRANCH)|stable)$$" || _NR=0;  echo $${_NR:-1}`

TIMESTAMP:=$${__TIMESTAMP:-$(shell /bin/date -u "+%Y%m%d%H%MZ")}
SHORT_SHA=`git rev-parse --short HEAD`
BRANCH=`git rev-parse --abbrev-ref HEAD | tr '-' '_'`

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
	@echo ""
	@echo "Possible use:"
	@echo "  make <target>"
	@echo "  PR=5 make <target>"
	@echo "  MR=6 <target>"
	@echo "  PR=7 SUFFIX='my_additional_suffix' make <target>"
	@echo "  MR=6 COPR_CONFIG='path/to/the/config/copr/file' <target>"
	@echo ""

clean:
	@echo "--- Clean repo ---"
	@rm -rf packaging/{sources,SRPMS,tmp}/
	@rm -rf build/ dist/ *.egg-info
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
	@echo copr --config $(_COPR_CONFIG) build $(_COPR_REPO_TMP) \
		packaging/SRPMS/${DEPS_PKGNAME}-${DEPS_VERSION}-${RELEASE}*.src.rpm
	@copr --config $(_COPR_CONFIG) build $(_COPR_REPO_TMP) \
		packaging/SRPMS/${DEPS_PKGNAME}-${DEPS_VERSION}-${RELEASE}*.src.rpm


copr_build: srpm
	@echo "--- Build RPM ${PKGNAME}-${VERSION}-${RELEASE}.el6.rpm in COPR ---"
	@echo copr --config $(_COPR_CONFIG) build $(_COPR_REPO) \
		packaging/SRPMS/${PKGNAME}-${VERSION}-${RELEASE}*.src.rpm
	@copr --config $(_COPR_CONFIG) build $(_COPR_REPO) \
		packaging/SRPMS/${PKGNAME}-${VERSION}-${RELEASE}*.src.rpm

print_release:
	@echo $(RELEASE)

# Before doing anything, it is good idea to register repos to ensure everything
# is in order inside ~/.config/leapp/repos.json
register:
	. tut/bin/activate; \
	snactor repo find --path repos

install-deps:
	virtualenv --system-site-packages -p /usr/bin/python2.7 tut; \
	. tut/bin/activate; \
	pip install --upgrade setuptools; \
	pip install --upgrade -r requirements.txt
	python utils/install_actor_deps.py --actor=$(ACTOR)

test:	lint
	. tut/bin/activate; \
	python utils/run_pytest.py --actor=$(ACTOR) --report=$(REPORT)

lint:
	. tut/bin/activate; \
	bash -c "find repos -name '*.py' | xargs pylint"; \
	flake8 repos

.PHONY: clean test install-deps build srpm

