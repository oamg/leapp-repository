import json
import os
from collections import defaultdict
from pathlib import Path

import rpm

from leapp.libraries.common.config.version import get_target_major_version
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api, run
from leapp.models import DistributionSignedRPM, UnsafePythonPaths

PYTHON_EXTENSIONS = (".py", ".so", ".pyc")

third_party_files = []
third_party_modules = []
rpms_to_check = defaultdict(list)


def get_python_sys_paths(python_interpreter):
    """Get sys.path from the specified Python interpreter."""

    result = run([python_interpreter, '-c', 'import sys, json; print(json.dumps(sys.path))'])['stdout']
    return json.loads(result)


def get_python_binary_for_rhel(rhel_version):
    """
    Maps RHEL major version to the appropriate Python binary.
    """

    version_map = {
        '9': 'python3.9',
        '10': 'python3.12',
    }
    return version_map[rhel_version]


def is_target_python_present(target_python):
    """
    Checks if the target Python interpreter is available on the system.
    """

    result = run(['/bin/sh', '-c', 'command -v {}'.format(target_python)], checked=False)
    return not result['exit_code']


def identify_files_of_pypackages(syspaths):
    ts = rpm.TransactionSet()
    # resolving paths to absolute paths and adding trailing slash
    roots = tuple(os.path.join(str(Path(path).resolve()), "") for path in syspaths)
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
    for pattern in PYTHON_EXTENSIONS:
        yield from Path(root).rglob("*" + pattern)


def process():
    target_python = get_python_binary_for_rhel(get_target_major_version())
    if not is_target_python_present(target_python):
        api.current_logger().info("Target Python interpreter {} is not installed on the source system, "
                                  "skipping check of 3rd party python modules.".format(target_python))
        return
    system_paths = get_python_sys_paths(target_python)
    rpm_files = identify_files_of_pypackages(system_paths[1:])

    for path in system_paths[1:]:
        print(path)
        if not Path(path).is_dir():
            continue
        for file in find_python_related(path):
            # pyc files are importable, but not if they are in __pycache__
            if file.name.endswith(".pyc") and file.parent.name == "__pycache__":
                continue
            owner = rpm_files.get(str(file))
            if owner:
                rpms_to_check[owner].append(file)
            else:
                third_party_files.append(file)

    for rpm_name, files in rpms_to_check.items():
        if not has_package(DistributionSignedRPM, rpm_name):
            third_party_modules.append(rpm_name)
            api.current_logger().warning(
                'Found Python files from non-distribution RPM package: {}'.format(rpm_name)
            )
            third_party_files.extend(files)

    if third_party_modules:
        api.current_logger().warning(
            'Found Python third-party modules: {}'.format(third_party_modules)
        )
        api.produce(UnsafePythonPaths(is_third_party_module_present=True,
                                      third_party_rpm_names=third_party_modules))
