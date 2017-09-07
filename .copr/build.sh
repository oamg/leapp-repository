#!/bin/bash
set -x

REPONAME=leapp-actors
SPECNAME=leapp-repository

OUTDIR="$PWD"
if [ -n "$1" ]; then
    OUTDIR="$(realpath $1)"
fi

command -v which > /dev/null || dnf -y install which

if [ -z "$(which git)" ]; then
    dnf -y install git-core
fi

if ! git status 2>&1 > /dev/null; then
    rm -rf leapp
    git clone https://github.com/leapp-to/$REPONAME
    POPD=`pushd leapp`
fi

BRANCH=master
LEAPP_PATCHES_SINCE_RELEASE="$(git log `git describe  --abbrev=0`..HEAD --format=oneline | wc -l)$LEAPP_PATCHES_SINCE_RELEASE_EXTERNAL"
echo LEAPP_PATCHES_SINCE_RELEASE=$LEAPP_PATCHES_SINCE_RELEASE$LEAPP_PATCHES_SINCE_RELEASE_EXTERNAL

VERSION=$(git describe  --abbrev=0|cut -d- -f 2)
DIST=$(git describe  --abbrev=0|cut -d- -f 3)
LEAPP_BUILD_TAG=".$DIST.$(date  --rfc-3339=date | tr -d '-').git.$LEAPP_PATCHES_SINCE_RELEASE"

if [ -n "$POPD" ]
then
    popd
fi


echo LEAPP_BUILD_TAG=$LEAPP_BUILD_TAG
export toplevel=$(git rev-parse --show-toplevel)
git archive --remote "$toplevel" --prefix $REPONAME-master/ HEAD > $REPONAME-$VERSION.tar
tar --delete $REPONAME-master/$SPECNAME.spec --file $REPONAME-$VERSION.tar
mkdir -p $REPONAME-master
/bin/cp $toplevel/$SPECNAME.spec $REPONAME-master/$SPECNAME.spec
sed -i "s/^%global dist.*$/%global dist $LEAPP_BUILD_TAG/g" $REPONAME-master/$SPECNAME.spec
tar --append --file $REPONAME-$VERSION.tar $REPONAME-master/$SPECNAME.spec

cat $REPONAME-$VERSION.tar | gzip > $REPONAME-$VERSION.tar.gz

echo $PWD $OUTDIR
SRPMDIR="$OUTDIR"
rpmbuild --define "_srcrpmdir $SRPMDIR" --define "version $VERSION" --define "gittag master" -ts ./$REPONAME-$VERSION.tar.gz

