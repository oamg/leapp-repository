from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import UnsafePythonPaths


def check_unsafe_python_paths(unsafe_paths):
    """Create an inhibitor when third-party Python modules are detected."""
    if not unsafe_paths.is_third_party_module_present:
        return

    third_party_rpms = unsafe_paths.third_party_rpm_names
    rpm_list = "\n".join([" - {}".format(rpm) for rpm in third_party_rpms])

    reporting.create_report([
        reporting.Title('Third-party Python modules detected in target Python environment'),
        reporting.Summary(
            'The target Python interpreter contains modules from RPM packages that are not '
            'signed by the distribution. These third-party Python modules may interfere with '
            'the upgrade process or cause unexpected behavior after the upgrade. '
            'The following non-distribution RPM packages contain Python modules:\n'
            '{}'.format(rpm_list)
        ),
        reporting.Remediation(
            hint='Remove or uninstall the third-party Python packages before attempting the upgrade. '
                 'You can reinstall them after the upgrade is complete if they are compatible with '
                 'the target system version.',
        ),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.INHIBITOR]),
    ])


def perform_check():
    """Perform the check for unsafe Python paths."""
    unsafe_paths_msg = next(api.consume(UnsafePythonPaths), None)
    if unsafe_paths_msg:
        check_unsafe_python_paths(unsafe_paths_msg)
