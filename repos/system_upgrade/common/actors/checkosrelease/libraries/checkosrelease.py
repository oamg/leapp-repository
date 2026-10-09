import os

from leapp import reporting
from leapp.libraries.common.config import version
from leapp.libraries.common.distro import DISTRO_REPORT_NAMES
from leapp.libraries.stdlib import api, format_list

COMMON_REPORT_TAGS = [reporting.Groups.SANITY]

related = [reporting.RelatedResource('file', '/etc/os-release')]


def skip_check():
    """ Check if an environment variable was used to skip this actor """
    if os.getenv('LEAPP_DEVEL_SKIP_CHECK_OS_RELEASE'):
        reporting.create_report([
            reporting.Title('Skipped OS release check'),
            reporting.Summary(
                'Source system release check skipped via LEAPP_DEVEL_SKIP_CHECK_OS_RELEASE env variable.'
            ),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups(COMMON_REPORT_TAGS)
        ] + related)

        return True
    return False


def _get_supported_source_versions():
    """Extract supported source versions from the upgrade paths configuration."""
    supported_upgrade_paths = api.current_actor().configuration.supported_upgrade_paths
    all_versions = sorted({path.source_version for path in supported_upgrade_paths})
    if '.' not in version.get_source_version():
        return all_versions
    return [v for v in all_versions if '.' in v]


def check_os_version():
    """ Check the distro version and inhibit the upgrade if it does not match the supported ones """
    if not version.is_supported_version():
        supported_source_versions = _get_supported_source_versions()
        prefix = DISTRO_REPORT_NAMES.source
        if api.current_actor().configuration.flavour == 'saphana':
            prefix = '{} (SAP HANA)'.format(prefix)
        supported_releases = ['{} {}'.format(prefix, v) for v in supported_source_versions]
        current_release = '{} {}'.format(prefix, version.get_source_version())
        reporting.create_report([
            reporting.Title(
                'The installed OS version is not supported for the in-place upgrade'
                ' to the target {target_distro} version'.format_map(DISTRO_REPORT_NAMES)
            ),
            reporting.Summary(
                'The supported OS releases for the upgrade process:'
                '{}\n\nThe detected OS release is: {}'.format(
                    format_list(supported_releases, callback_sort=None),
                    current_release)
            ),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups(COMMON_REPORT_TAGS),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            # we want to set a static Key here because of different Title per path
            reporting.Key('1c7a98849a747ec9890f04bf4321de7280970715')
        ] + related)
