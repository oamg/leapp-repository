#!/usr/bin/python
# A top level script for stub *generation* - not the final assembly, for that
# see gen_stubs.sh
# All the generation is kept in a python script to save some time on
# interpreter executions and initialization.

import argparse
import sys
from pathlib import Path

import gen_model_stubs
from mypy import stubgen

SYS_UPG_REPOS_PATH = Path("repos/system_upgrade/")
REPOS = ["common", "el8toel9", "el9toel10"]


def run_stubgen(paths: Path | list[Path], output_dir: Path):
    """
    Calls stubgen.main() directly.
    'paths' can be a single string/Path or a list of them.
    """

    if not isinstance(paths, list):
        paths_str = [str(paths)]
    else:
        paths_str = [str(p) for p in paths]

    opts = stubgen.Options(
        output_dir=str(output_dir),
        files=paths_str,
        modules=[],
        packages=[],
        search_path=[""],
        ignore_errors=True,
        export_less=False,
        include_docstrings=True,
        include_private=False,
        inspect=False,
        no_import=False,
        parse_only=False,
        pyversion=sys.version_info[:2],
        quiet=True,
        verbose=False,
        doc_dir="",
        interpreter="/usr/bin/python",
    )

    try:
        stubgen.generate_stubs(opts)
    except SystemExit as e:
        # stubgen calls sys.exit(0) on success; we catch it to prevent
        # the entire script from exiting.
        print("here")
        if e.code != 0:
            print(f"Stubgen failed for {paths_str} with exit code {e.code}")


def generate_all(out_dir: Path):
    # 1. Standard library/tags/topics processing
    print("Generating stubs for common/libraries")
    run_stubgen(SYS_UPG_REPOS_PATH / "common/libraries/", out_dir / "libraries/common")
    print("Generating stubs for common/tags")
    run_stubgen(SYS_UPG_REPOS_PATH / "common/tags/", out_dir / "tags")
    print("Generating stubs for common/topics")
    run_stubgen(SYS_UPG_REPOS_PATH / "common/topics/", out_dir / "topics")

    # SystemFactsTopic lives in the common repo
    run_stubgen(Path("repos/common/topics/"), out_dir / "topics")

    # 2. Setup models directory
    (out_dir / "models").mkdir(parents=True, exist_ok=True)

    # 3. Process repos by priority
    for repo in REPOS:
        repo_path = SYS_UPG_REPOS_PATH / repo

        actor_libs = list((repo_path / "actors").rglob("*/libraries/*.py"))
        if actor_libs:
            print(f"Generating stubs for {repo} actors libraries")
            run_stubgen(actor_libs, out_dir / "libraries/actor")

    for repo in REPOS:
        repo_path = SYS_UPG_REPOS_PATH / repo

        print(f"Generating stubs for {repo}/models")
        models = (repo_path / "models").rglob("*.py")
        for model_file in models:
            gen_model_stubs.main(model_file, out_dir / "models")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-o", "--out-dir", type=Path, required=True, help="Path to the output directory"
    )

    args = parser.parse_args()

    generate_all(args.out_dir)


if __name__ == "__main__":
    main()
