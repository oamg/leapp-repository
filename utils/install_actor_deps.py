"""
Script for installing dependencies for specific actor.
It is called from Makefile install-deps target.
If given actor doesn't exist, script exits with return
code 1 and stderr message.
If given actor doesn't have Makefile, warning printed on stderr.
If no actor is specified dependencies will be installed
for all actors with Makefile.

usage: python install_actor_deps.py [--actor actorname]
"""

import argparse
import os
import sys
from subprocess import check_call, CalledProcessError


def error(msg, rc):
    sys.stderr.write(msg)
    sys.exit(rc)


def install(path):
    cmd = "make -f {} install-deps".format(path)
    try:
        check_call(cmd, shell=True)
    except CalledProcessError as e:
        error(str(e) + '\n', e.returncode)


def install_actor_deps(actor, directory):
    for root, dirs, files in os.walk(directory):
        if actor in dirs:
            makefile_path = os.path.join(root, actor, 'Makefile')
            if os.path.isfile(makefile_path):
                install(makefile_path)
            else:
                sys.stderr.write("Actor '{}' doesn't have Makefile!\n".format(actor))
            return
    error("Actor '{}' doesn't exist!\n".format(actor), 1)


def install_all_deps(directory, repos):
    repos = repos.split() if repos else repos
    for root, dirs, files in os.walk(directory):
        if repos and not any([repo in dirs for repo in repos]):
            continue
        if 'Makefile' in files:
            install(os.path.join(root, 'Makefile'))


if __name__ == "__main__":
    ACTORS_DIR = './repos'

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--actor", help="name of the actor for which to install dependencies")
    parser.add_argument(
        "--repos", help="repositories to look into")
    args = parser.parse_args()

    if args.actor:
        install_actor_deps(args.actor, ACTORS_DIR)
    else:
        install_all_deps(ACTORS_DIR, args.repos)
