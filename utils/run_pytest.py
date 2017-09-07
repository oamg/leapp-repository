"""
tmeszaro@redhat.com

This script is called by the make test target.


There can be two arguments:

 1. ACTOR=myactor

    NOTE: This is currently disabled, we will enable this when the CI will
          support "one actor, one container" testing.

 2. REPORT=myreport.xml

    Outputs xml report for the JUnit.


What is happening

 1. Checks cmd line arguments. There can be ACTOR and REPORT.

 2. Finds and registers all leapp repos in the BASE_REPO path.

 3. Checks if there are actor tests present.

 4. Runs pytest for each actor in BASE_REPO path.

 5. Combines reports from pytest runs if requested by --report argument
"""

import argparse
from glob import glob
import logging
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

from leapp.repository.scan import find_and_scan_repositories

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("run_pytest.py")

BASE_REPO = "repos"
REPORT_DIR = "reports/"


def snactor_register(path):
    """ Snactor registers all repos in @path.
    """
    cmd = "snactor repo find --path {PATH}".format(PATH=path)
    try:
        logger.info(" Registering leapp repositories. This may take a while.")
        return subprocess.check_output(cmd, shell=True)
    except OSError as exc:
        sys.stderr.write(str(exc) + '\n')
        return None


def combine_pytest_xmls(first, second):
    first.attrib.update({
        'errors': str(int(first.attrib['errors']) + int(second.attrib['errors'])),
        'failures': str(int(first.attrib['failures']) + int(second.attrib['failures'])),
        'skips': str(int(first.attrib['skips']) + int(second.attrib['skips'])),
        'tests': str(int(first.attrib['tests']) + int(second.attrib['tests'])),
        'time': str(float(first.attrib['time']) + float(second.attrib['time'])),
    })
    first.extend(second.findall('testcase'))


def produce_report(reports_dir, path):
    reports = (glob(reports_dir + '*.xml'))
    trees = [ET.parse(f) for f in reports]
    root = trees[0].getroot()
    for tree in trees[1:]:
        combine_pytest_xmls(root, tree.getroot())

    trees[0].write(path, encoding='utf-8', xml_declaration=True)


if __name__ == "__main__":
    pytest_cmd = ["pytest", "-v"]
    pytest_status = set()

    parser = argparse.ArgumentParser()
    parser.add_argument("--actor", help="name of the actor for which to run tests")
    parser.add_argument("--report", help="filepath where to save report")
    args = parser.parse_args()

    # User wants to test single actor specified in the args.actor.
    if args.actor:
        # NOTE: ACTOR flag is disabled. Check module docstring for more info.
        logger.critical(" ACTOR flag is currently disabled!")
        sys.exit(1)

    shutil.rmtree(REPORT_DIR, ignore_errors=True)
    os.mkdir(REPORT_DIR)

    # Register repos.
    snactor_register(BASE_REPO)

    # Find and collect leapp repositories.
    repos = find_and_scan_repositories(BASE_REPO, include_locals=True)
    repos.load()

    for i, actor in enumerate(repos.actors):
        # Run tests if actor has any.
        if not actor.tests:
            status = " Tests MISSING: {ACTOR} | class={CLASS}"
            status = status.format(ACTOR=actor.name, CLASS=actor.class_name)
            logger.critical(status)
        else:
            os.environ['LEAPP_TESTED_ACTOR'] = actor.full_path
            cmd = pytest_cmd + [actor.full_path]
            if args.report:
                cmd += ['--junit-xml={REPORT}'.format(REPORT=REPORT_DIR + actor.name + str(i) + '.xml')]
            # Run pytest.
            logger.info(" Running pytest with: {PYTEST_CMD}".format(PYTEST_CMD=' '.join(cmd)))
            pytest_status.add(subprocess.call(cmd))

    if args.report:
        produce_report(REPORT_DIR, args.report)
    # Cleanup.
    shutil.rmtree(REPORT_DIR)
    sys.exit(max(pytest_status))
