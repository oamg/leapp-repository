from leapp import reporting
from leapp.libraries.common.config.architecture import ARCH_ARM64, matches_architecture
from leapp.libraries.common.config.version import get_source_version, get_target_version
from leapp.libraries.stdlib import api


def _inhibit_upgrade():
    title = 'Upgrade {} to {} unsupported for ARM machines.'.format(
        get_source_version(), get_target_version())
    summary = ('Due to the incompatibility of the RHEL8 bootloader with a '
               'newer version of kernel on RHEL9 a direct upgrade '
               'cannot be performed for versions 9.5 and up.')

    reporting.create_report([
        reporting.Title(title),
        reporting.Summary(summary),
        reporting.ExternalLink(
            title='Known issues for the RHEL 8.10 to RHEL 9.5 upgrade',
            url='https://red.ht/upgrading-rhel8-to-rhel9-known-issues'),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.INHIBITOR]),
        reporting.Groups([reporting.Groups.SANITY]),
        reporting.Remediation(hint=(
            'To upgrade to a RHEL version 9.5 and up, first perform an upgrade '
            'to version 9.4 using the leapp `--target` option and then perform '
            'a minor dnf update after the upgrade')),
    ])


def process():
    """
    Check whether the upgrade path will use a target kernel compatible with the source bootloader on ARM systems
    """

    if not matches_architecture(ARCH_ARM64):
        api.current_logger().info('Architecture not ARM. Skipping bootloader check.')
        return

    target_major, target_minor = tuple(map(int, get_target_version().split('.')))
    if (target_major, target_minor) < (9, 5):
        api.current_logger().info((
            'Upgrade on ARM architecture on a compatible path ({} to {}). '
            'Skipping bootloader check.').format(get_source_version(), get_target_version()))
        return

    _inhibit_upgrade()
