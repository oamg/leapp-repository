__PKGNAME=$${_PKGNAME:-leapp-repository}
__DATA_ORIG_PKGNAME=$${_DATA_ORIG_PKGNAME:-leapp-pes-data}
PKGNAME=leapp-repository
VERSION=`grep -m1 "^Version:" packaging/$(PKGNAME).spec | grep -om1 "[0-9].[0-9.]**"`

# by default use values you can see below, but in case the COPR_* var is defined
# use it instead of the default
_COPR_REPO=$${COPR_REPO:-leapp}
_COPR_CONFIG=$${COPR_CONFIG:-~/.config/copr_rh_oamg.conf}

# just to reduce number of unwanted builds mark as the upstream one when
# someone will call copr_build without additional parameters
MASTER_BRANCH=master

# In case the PR or MR is defined or in case build is not comming from the
# MATER_BRANCH branch, N_REL=0; (so build is not update of the approved
# upstream solution). For upstream builds N_REL=1;
N_REL=`_NR=$${PR:+0}; if test "$${_NR:-1}" == "1"; then _NR=$${MR:+0}; fi; git rev-parse --abbrev-ref HEAD | grep -qE "^($(MASTER_BRANCH)|stable)$$" || _NR=0;  echo $${_NR:-1}`

TIMESTAMP:=$${__TIMESTAMP:-$(shell /bin/date "+%Y%m%d%H%MZ" -u)}
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

list_builds:
	@copr --config $(_COPR_CONFIG) get-package $(_COPR_REPO) \
		--name $(__PKGNAME) --with-all-builds \
		| grep -E '"(built_packages|id|state|pkg_version)"' | grep -B3 "succeeded" \
		| sed 's/"state": "succeeded",/----------------------/' \
		| grep -A1 -B2 '"pkg_version".*-[1-9]'

source: prepare
	@echo "--- Create source tarball ---"
	@echo git archive --prefix "$(PKGNAME)-$(VERSION)/" -o "packaging/sources/$(PKGNAME)-$(VERSION).tar.gz" HEAD
	@git archive --prefix "$(PKGNAME)-$(VERSION)/" -o "packaging/sources/$(PKGNAME)-$(VERSION).tar.gz" HEAD
	@echo "--- Download $(PKGNAME)-initrd SRPM ---"
	@copr --config $(_COPR_CONFIG) download-build -d packaging/tmp \
		`_PKGNAME=$(PKGNAME)-initrd __TIMESTAMP=$(TIMESTAMP) $(MAKE) list_builds | grep -m1 '"id"' | grep -o "[0-9][0-9]*"`
	@echo "--- Get $(PKGNAME)-initrd  tarball---"
	@rpm2cpio `find packaging/tmp | grep -m1 "src.rpm$$"` > packaging/tmp/$(PKGNAME)-initrd.cpio
	@cpio -iv --no-absolute-filenames --to-stdout "$(PKGNAME)-initrd-*.tar.gz" \
		<packaging/tmp/$(PKGNAME)-initrd.cpio \
		>packaging/sources/$(PKGNAME)-initrd.tar.gz
		# -- it is easier to use here static name ot the initrd tarball; the rest can be handled easier
		# >packaging/sources/`cpio -t <packaging/tmp/$(PKGNAME)-initrd.cpio | grep '$(PKGNAME)-initrd.*tar.gz'`
	@rm -rf packaging/tmp/*
	@echo "--- Download $(__DATA_ORIG_PKGNAME) SRPM ---"
	@copr --config $(_COPR_CONFIG) download-build -d packaging/tmp \
		`_PKGNAME=$(__DATA_ORIG_PKGNAME) __TIMESTAMP=$(TIMESTAMP) $(MAKE) list_builds | grep -m1 '"id"' | grep -o "[0-9][0-9]*"`
	@echo "--- Get $(__DATA_ORIG_PKGNAME) tarball---"
	@rpm2cpio `find packaging/tmp | grep -m1 "src.rpm$$"` > packaging/tmp/$(__DATA_ORIG_PKGNAME).cpio
	@cpio -iv --no-absolute-filenames --to-stdout "$(__DATA_ORIG_PKGNAME)-*.tar.gz" \
		<packaging/tmp/$(__DATA_ORIG_PKGNAME).cpio \
		>packaging/sources/$(PKGNAME)-data.tar.gz
		# yes - the final tarball rename to $(PKGNAME)-data
	#@rm -rf packaging/tmp

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
	virtualenv -p /usr/bin/python2.7 tut; \
	. tut/bin/activate; \
	pip install --upgrade setuptools; \
	pip install -r requirements.txt
	python utils/install_actor_deps.py --actor=$(ACTOR)

test:
	. tut/bin/activate; \
	python utils/run_pytest.py --actor=$(ACTOR) --report=$(REPORT)

.PHONY: clean test install-deps build srpm

