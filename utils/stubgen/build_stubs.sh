#!/bin/bash
set -uo pipefail

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <tmp_dir> <output_dir>"
    exit 1
fi

TMP_DIR="$1"
OUT_DIR="$2"

if [ ! -d "$TMP_DIR" ]; then
    mkdir -p "$TMP_DIR"
fi

if [ ! -d "$OUT_DIR" ]; then
    mkdir -p "$OUT_DIR"
fi


# all the generation code is written in a python script to save time on the
# Python interpreter and mypy initializiaton when executing mypy.stubgen
if ! ./utils/stubgen/gen_stubs.py --out-dir "$TMP_DIR"; then
    echo "Error: Stub generation failed." >&2
    exit 1
fi

# Assemble final outputs
# Models, topics and tags need to be flattened into a singled __init__.py file
# to simulate how they are loaded into e.g. leapp.models. The imports are
# hardcoded at the top and then stripped from all the .pyi files to avoid
# repeating them.
#
# Actor and common libs are more straightforward since they are in separate
# dynamically loaded modules in leapp.
echo "Assembling final stubs in '${OUT_DIR}'."
mkdir -p "${OUT_DIR}"/leapp/{models,tags,topics} "${OUT_DIR}"/leapp/libraries/{common,actor}

# Models
# flake checks the code in the heredoc, so let's keep it conforming
cat <<EOF > "${OUT_DIR}/leapp/models/__init__.pyi"
from typing import Any, Literal

from _typeshed import Incomplete

from leapp.models import Model
from leapp.topics import (
    BootPrepTopic,
    RHSMTopic,
    SystemFactsTopic,
    SystemInfoTopic,
    TargetUserspaceTopic,
    TransactionTopic
)


class Report: ...
EOF
find "$TMP_DIR/models" -name "*.pyi" -exec cat {} + | sed '/^from .* import .*/d' >> "${OUT_DIR}/leapp/models/__init__.pyi"

# Tags
echo 'from leapp.tags import Tag' > "${OUT_DIR}/leapp/tags/__init__.pyi"
find "$TMP_DIR/tags" -name "*.pyi" -exec cat {} + | sed '/^from .* import .*/d' >> "${OUT_DIR}/leapp/tags/__init__.pyi"

# Topics
echo 'from leapp.topics import Topic' > "${OUT_DIR}/leapp/topics/__init__.pyi"
find "$TMP_DIR/topics" -name "*.pyi" -exec cat {} + | sed '/^from .* import .*/d' >> "${OUT_DIR}/leapp/topics/__init__.pyi"

# libs
# build a __init__.pyi with reimports of the libraries
# this is required to resolve import of this form:
#   from leapp.libraries.common import <library>
# NOTE: this shadows the real __init__.py, however it doesn't really
# contain anything interesting for development
#
# __init__.pyi is excluded in case this is not a clean generation
find "${TMP_DIR}/libraries/common" \
    -maxdepth 1 \
    -mindepth 1 \
    -not -name 'test_*' \
    -not -name '__init__.pyi' \
    -printf '%f\n' \
    | while read -r mod;
do
    mod_name="${mod%.*}"
    echo "from . import $mod_name as $mod_name" >> "${TMP_DIR}/libraries/common/__init__.pyi"
done

rsync -a --delete "${TMP_DIR}/libraries/common" "${OUT_DIR}/leapp/libraries"
rsync -a --delete "${TMP_DIR}/libraries/actor" "${OUT_DIR}/leapp/libraries"

echo "Removing temp dir at ${TMP_DIR}"
rm -r "$TMP_DIR"

echo "Done."
