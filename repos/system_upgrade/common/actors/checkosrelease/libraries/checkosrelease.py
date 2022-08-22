import os

from leapp import reporting
from leapp.libraries.common.config import version

COMMON_REPORT_TAGS = [reporting.Groups.SANITY]

related = [reporting.RelatedResource('file', '/etc/os-release')]


def skip_check():
    """ Check if an environment variable was used to skip this actor """
    if os.getenv('LEAPP_DEVEL_SKIP_CHECK_OS_RELEASE'):
        reporting.create_report([
            reporting.Title('Skipped OS release check'),
            reporting.Summary('Source RHEL release check skipped via LEAPP_DEVEL_SKIP_CHECK_OS_RELEASE env var.'),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups(COMMON_REPORT_TAGS)
        ] + related)

        return True
    return False


def check_os_version():
    """ Check the RHEL minor version and inhibit the upgrade if it does not match the supported ones """
    if not version.is_supported_version():
        supported_releases = []
        for rel in version.SUPPORTED_VERSIONS:
            for ver in version.SUPPORTED_VERSIONS[rel]:
                supported_releases.append(rel.upper() + ' ' + ver)
        reporting.create_report([
            reporting.Title(
                'The installed OS version is not supported for the in-place upgrade to the target RHEL version'
            ),
            reporting.Summary(
                'The supported OS releases for the upgrade process:\n'
                ' {}'.format('\n'.join(supported_releases))
            ),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups(COMMON_REPORT_TAGS),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            # we want to set a static Key here because of different Title per path
            reporting.Key('1c7a98849a747ec9890f04bf4321de7280970715')
        ] + related)
