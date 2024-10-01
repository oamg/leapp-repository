SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
SPHINXAUTOBUILD = sphinx-autobuild
SPHINXPROJ    = Leapp repository
SOURCEDIR     = source
BUILDDIR      = build

all: clean html

help:
	@source venv/bin/activate && \
	$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
livehtml:
	@source venv/bin/activate && \
	$(SPHINXAUTOBUILD) --watch ../repos --watch ../commands "$(SOURCEDIR)" "$(BUILDDIR)/html" $(SPHINXOPTS) $(0)

# Prepare virtualenv similar to the environment used during build on Read The Docs and install required packages
env:
	@PY_VER=$$(sed -n -e 's/^\s*python:\s"\(.*\)"/\1/p' ../.readthedocs.yaml); \
	rm -fr ./venv; \
	virtualenv venv --python=python$$PY_VER && \
	source venv/bin/activate && \
	pip install -r requirements-docs.txt;

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@source venv/bin/activate && \
	$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: all help Makefile env
