import os
import re

from leapp import reporting
from leapp.libraries.common.config import version
from leapp.libraries.stdlib import api, run

FMT_LIST_SEPARATOR = '\n    - '


def find_python_executables():
    python_executables = set()
    whereis_result = run(['whereis', '-b', 'python'])['stdout']
    paths = whereis_result.split()[1:]  # Remove the "python: " from start
    for path in paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            try:
                # Verify it's a Python executable
                version = run([path, '--version'], checked=False)
                if version['exit_code'] != 0:
                    continue

                if version['stdout'].startswith('Python'):
                    python_executables.add(os.path.realpath(path))
            except Exception as e:
                api.current_logger().info('Skipping path {path} for inspection of python modules: {e}'
                                          .format(path=path, e=e))

    return list(python_executables)


def get_python_sys_paths(python_executables):
    all_paths = set()
    for exe_path in python_executables:
        site_result = run([exe_path, '-m', 'site'])['stdout']
        parsed_paths = parse_site_output(site_result)
        all_paths.update(parsed_paths)
    return all_paths


def parse_site_output(output):
    paths = set()
    in_syspath = False

    for line in output.split('\n'):
        line = line.strip()
        if line.startswith('sys.path = ['):
            in_syspath = True
            continue

        if in_syspath:
            if line == ']':
                break

            # Extract path from quoted string, handling single or double quotes
            match = re.search(r"'(.*?)'|\"(.*?)\"", line)
            if match:
                path = match.group(1) if match.group(1) is not None else match.group(2)
                if path:
                    paths.add(path)
    return paths


def is_rpm_owned(path):
    if not os.path.exists(path):
        return False

    rpm_result = run(['rpm', '-qf', path], checked=False)
    # If return code is 0 and stdout is not empty, it's RPM-owned
    return rpm_result['exit_code'] == 0 and rpm_result['stdout'].strip() != ""


def identify_third_party_modules(all_paths):
    third_party_modules = {}
    processed_module_paths = set()

    dirs = sorted([p for p in all_paths if os.path.isdir(p)])

    for dir_path in dirs:
        try:
            for item in os.listdir(dir_path):
                full_item_path = os.path.join(dir_path, item)

                if full_item_path in processed_module_paths:
                    continue

                if os.path.isdir(item) and item.endswith(('.egg-info', '.dist-info')):
                    if item not in third_party_modules and not is_rpm_owned(full_item_path):
                            third_party_modules[item] = full_item_path
                            processed_module_paths.add(full_item_path)
        except PermissionError:
            api.current_logger().error('Insufficient access permission for path {path}'.format(path=dir_path))
        except Exception as e:
            api.current_logger().error('Unexpedted error for path {path}: {e}'.format(path=dir_path, e=e))

    api.current_logger().info("Identified 3rd-party modules: {modules} .".format(modules=third_party_modules))
    return third_party_modules


def process():
    executables = find_python_executables()

    all_site_paths = get_python_sys_paths(executables)
    third_party_modules = identify_third_party_modules(all_site_paths)

    all_unsafe_paths = list(third_party_modules.values())

    if all_unsafe_paths: 
        sorted_unsafe_paths = sorted(all_unsafe_paths)
        formatted_paths_for_summary = ', '.join(sorted_unsafe_paths)

        reporting.create_report([
            reporting.Title('Third-party Python modules detected in system paths'),
            reporting.Summary(
                'The following directories containing third-party Python modules were detected: {}. '
                'These may interfere with the upgrade process or break critical system tools after the upgrade. '
                .format(''.join(['{}{}'.format(FMT_LIST_SEPARATOR, path) for path in formatted_paths_for_summary]))
            ),
            reporting.Groups([reporting.Groups.PYTHON]),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Remediation(hint=(
                'Review and remove unnecessary third-party Python modules from the directories'
                'Consider using Python virtual environments (e.g., venv, virtualenv)'))
        ])
    else:
        api.current_logger().info("No non-RPM-owned third-party Python modules detected.")
