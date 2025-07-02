import os

from leapp import reporting
from leapp.libraries.common.config import version
from leapp.libraries.stdlib import api


def process():
    source_version = version.get_source_major_version()

    # Mapping: source version → unsafe path
    version_map = {
        '8':  '/usr/lib/python3.9',
        '9': '/usr/lib/python3.12',
    }

    unsafe_path = version_map.get(source_version)
    if not unsafe_path or not os.path.isdir(unsafe_path):
        api.current_logger().info('No 3rd party Python modules found, skipping...')
        return

    reporting.create_report([
        reporting.Title('Third-party Python modules detected in system paths'),
        reporting.Summary(
            'The following directories containing third-party Python modules were detected: {path}. '
            'These may interfere with the upgrade process or break critical system tools after the upgrade. '
            .format(path=unsafe_path)
        ),
        reporting.Groups([reporting.Groups.PYTHON]),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.RelatedResource('Unsafe directories', unsafe_path),
        reporting.Remediation(hint=(
            'Review and remove unnecessary third-party Python modules from the following directories: {path}. '
            .format(path=unsafe_path)
        ))
    ])
