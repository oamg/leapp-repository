import json
import os
from collections import defaultdict
from pathlib import Path

import rpm

from leapp.libraries.common.config.version import get_target_major_version
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api, run
from leapp.models import DistributionSignedRPM, ThirdPartyTargetPythonModules

PYTHON_EXTENSIONS = (".py", ".so", ".pyc")
FMT_LIST_SEPARATOR = '\n  - '


def _formatted_list_output(input_list, sep=FMT_LIST_SEPARATOR):
    return ['{}{}'.format(sep, item) for item in input_list]


def get_python_sys_paths(python_interpreter):
    """Get sys.path from the specified Python interpreter."""

    result = run([python_interpreter, '-c', 'import sys, json; print(json.dumps(sys.path))'])['stdout']
    raw_paths = json.loads(result)
    paths = [Path(raw_path).resolve() for raw_path in raw_paths]
    return paths


def get_python_binary_for_rhel(rhel_version):
    """
    Maps RHEL major version to the appropriate Python binary.
    """

    version_map = {
        '9': 'python3.9',
        '10': 'python3.12',
    }
    return version_map.get(rhel_version)


def is_target_python_present(target_python):
    """
    Checks if the target Python interpreter is available on the system.
    """

    result = run(['command', '-v', target_python], checked=False)
    return not result['exit_code']


def identify_files_of_pypackages(syspaths):
    ts = rpm.TransactionSet()
    # add a trailing slash by calling os.path.join(..., '')
    roots = tuple(os.path.join(str(path), "") for path in syspaths)
    file_to_pkg = {}

    # Iterate over all installed packages
    for header in ts.dbMatch():
        pkg = header['name']
        files = header['filenames']
        for filename in files:
            if filename and filename.endswith(PYTHON_EXTENSIONS) and filename.startswith(roots):
                file_to_pkg[filename] = pkg
    return file_to_pkg


def find_python_related(root):
    # recursively search for all files matching the given extension
    for pattern in PYTHON_EXTENSIONS:
        yield from root.rglob("*" + pattern)


def _should_skip_file(file):
    # pyc files are importable, but not if they are in __pycache__
    return file.name.endswith(".pyc") and file.parent.name == "__pycache__"


def scan_python_files(system_paths, rpm_files):
    """
    Scan system paths for Python files and categorize them by ownership.

    :param system_paths: List of paths to scan for Python files
    :param rpm_files: Dictionary mapping file paths to RPM package names
    :return: Tuple of (rpms_to_check, third_party_unowned_files) where:
             - rpms_to_check is a dict mapping RPM names to list of their files
             - third_party_unowned_files is a list of files not owned by any RPM
    """
    rpms_to_check = defaultdict(list)
    third_party_unowned_files = []

    for path in system_paths:
        if not path.is_dir():
            continue
        for file in find_python_related(path):
            if _should_skip_file(file):
                continue

            file_path = str(file)
            owner = rpm_files.get(file_path)
            if owner:
                rpms_to_check[owner].append(file_path)
            else:
                third_party_unowned_files.append(file_path)

    return rpms_to_check, third_party_unowned_files


def identify_unsigned_rpms(rpms_to_check):
    """
    Identify which RPMs are third-party (not signed by the distribution).

    :param rpms_to_check: Dictionary mapping RPM names to list of their files
    :return: Tuple of (third_party_rpms, third_party_files) where:
             - third_party_rpms is a list of third-party RPM package names
             - third_party_files is a list of files from third-party RPMs
    """
    third_party_rpms = []
    third_party_files = []

    for rpm_name, files in rpms_to_check.items():
        if not has_package(DistributionSignedRPM, rpm_name):
            third_party_rpms.append(rpm_name)
            api.current_logger().warning(
                'Found Python files from non-distribution RPM package: {}'.format(rpm_name)
            )
            third_party_files.extend(files)

    return third_party_rpms, third_party_files


def process():
    """
    Main function to scan for third-party Python modules/RPMs on the target system.

    This function:
    1. Validates the target RHEL version and Python interpreter
    2. Scans system paths for Python files
    3. Identifies third-party RPMs and modules
    4. Produces a message if any third-party modules/RPMs are detected
    """
    target_version = get_target_major_version()
    target_python = get_python_binary_for_rhel(target_version)

    if not target_python:
        api.current_logger().info(
            "RHEL version {} is not supported for third-party Python modules scanning, "
            "skipping check.".format(target_version)
        )
        return

    if not is_target_python_present(target_python):
        api.current_logger().info(
            "Target Python interpreter {} is not installed on the source system, "
            "skipping check of 3rd party python modules.".format(target_python)
        )
        return
    system_paths = get_python_sys_paths(target_python)
    rpm_files = identify_files_of_pypackages(system_paths[1:])

    rpms_to_check, third_party_unowned_files = scan_python_files(system_paths[1:], rpm_files)

    third_party_rpms, third_party_rpm_files = identify_unsigned_rpms(rpms_to_check)

    # Combine all third-party files (unowned + from third-party RPMs)
    all_third_party_files = third_party_unowned_files + third_party_rpm_files

    if third_party_rpms or all_third_party_files:
        api.current_logger().warning(
            'Found {} third-party RPM package(s) and {} third-party Python file(s) '
            'for target Python {}'.format(
                len(third_party_rpms), len(all_third_party_files), target_python
            )
        )

        if third_party_rpms:
            api.current_logger().info(
                'Complete list of third-party RPM packages:{}'.format(
                    ''.join(_formatted_list_output(third_party_rpms))
                )
            )

        if all_third_party_files:
            api.current_logger().info(
                'Complete list of third-party Python modules:{}'.format(
                    ''.join(_formatted_list_output(all_third_party_files))
                )
            )

        api.produce(ThirdPartyTargetPythonModules(
            target_python=target_python,
            third_party_modules=all_third_party_files,
            third_party_rpm_names=third_party_rpms
        ))
