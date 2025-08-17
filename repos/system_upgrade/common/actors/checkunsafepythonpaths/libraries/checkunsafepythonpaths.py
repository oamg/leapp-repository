import os
import re

# from leapp import reporting
from leapp.libraries.common.config.version import get_target_major_version
from leapp.libraries.common.distro import get_distribution_data
from leapp.libraries.stdlib import api, CalledProcessError, run


# FMT_LIST_SEPARATOR = '\n    - '


def _is_distro_signed(pgpsig, distro_keys):
    return any(key in pgpsig for key in distro_keys)


def get_python_sys_paths(python_interpreter):
    all_paths = set()
    site_result = run([python_interpreter, '-m', 'site'])['stdout']
    parsed_paths = parse_site_output(site_result)
    all_paths.update(parsed_paths)
    return all_paths


def parse_site_output(output):
    """Parse the output of 'python -m site' to extract sys.path entries."""

    paths = set()
    in_syspath = False
    path_regex = re.compile(r"""['"]([^'"]+)['"]""")  # Match string inside quotes

    for line in output.splitlines():
        line = line.strip()

        if line.startswith("sys.path = ["):
            in_syspath = True
            continue

        if in_syspath:
            if line == "]":
                break

            match = path_regex.search(line)
            if match:
                paths.add(match.group(1))
    return paths


def _get_rpm_name(path):
    if not os.path.exists(path):
        return False

    try:
        rpm_names = run(['rpm', '-qf', '--queryformat', r'%{NAME}\n', path], split=True)['stdout']
    except CalledProcessError:
        # Is not owned by any rpm
        return ''

    return rpm_names[0]


def rpm_is_rh_signed(rpm_name):
    """
    Check if the RPM package is signed by Red Hat.
    """

    distro_keys = get_distribution_data('rhel').get('distro_keys', [])

    pgpsig = run(['rpm', '-q', '--qf', '%{SIGPGP:pgpsig}', rpm_name], split=True)['stdout']
    return _is_distro_signed(pgpsig, distro_keys)


def identify_third_party_modules(all_paths):
    third_party_modules = {}
    processed_module_paths = set()

    dirs = sorted([p for p in all_paths if os.path.isdir(p)])

    for dir_path in dirs:
        try:
            for module in os.listdir(dir_path):
                full_module_path = os.path.join(dir_path, module)

                if not os.path.exists(os.path.join(full_module_path, '__init__.py')):
                    continue # Not a Python package

                if full_module_path in processed_module_paths:
                    continue

                rpm = _get_rpm_name(full_module_path)

                if rpm_is_rh_signed(rpm):
                    continue
                third_party_modules[module] = full_module_path
                processed_module_paths.add(full_module_path)

        except PermissionError:
            api.current_logger().error('Insufficient access permission for path {path}'.format(path=dir_path))

    return third_party_modules


def get_python_binary_for_rhel(rhel_version):
    """
    Maps RHEL major version to the appropriate Python binary.
    """

    version_map = {
        9: 'python3.9',
        10: 'python3.12',
    }
    return version_map[rhel_version]


def is_target_python_present(target_python):
    """
    Checks if the target Python interpreter is available on the system.
    """

    result = run(['which', target_python], checked=False)
    return not result['exit_code']


def process():
    target_python = get_python_binary_for_rhel(get_target_major_version())
    if not is_target_python_present(target_python):
        api.current_logger().info("Target Python interpreter {} is not available, "
                                  "skipping check of 3rd party python modules.".format(target_python))
        return

    target_python_sys_paths = get_python_sys_paths(target_python)

    third_party_modules = identify_third_party_modules(target_python_sys_paths)
    if not third_party_modules:
        api.current_logger().info("No third-party Python modules found in sys.path.")
        return

    # all_unsafe_paths = list(third_party_modules.values())
    # report ...
