SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
SPHINXAUTOBUILD = sphinx-autobuild
SPHINXPROJ    = Leapp repository
SOURCEDIR     = source
BUILDDIR      = build

all: clean html

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
livehtml:
	@$(SPHINXAUTOBUILD) --watch ../repos --watch ../commands "$(SOURCEDIR)" "$(BUILDDIR)/html" $(SPHINXOPTS) $(0)

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	echo $@
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: all help Makefile
