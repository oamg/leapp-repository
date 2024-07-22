from leapp import reporting
from leapp.libraries.common.config.architecture import ARCH_ARM64, matches_architecture
from leapp.libraries.common.config.version import get_source_version, get_target_version, matches_target_version
from leapp.libraries.stdlib import api


def _inhibit_upgrade():
    title = 'Upgrade RHEL {} to RHEL {} not possible for ARM machines.'.format(
        get_source_version(), get_target_version())
    summary = (
        'Due to the incompatibility of the RHEL 8 bootloader with a newer version of kernel on RHEL {}'
        ' for ARM machines, the direct upgrade cannot be performed to this RHEL'
        ' system version now. The fix is not expected to be delivered during the RHEL 9.5 lifetime.'
        .format(get_target_version())
    )

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
            'To upgrade to the RHEL {} version, first in-place upgrade to RHEL 9.4 instead'
            ' using the leapp `--target=9.4` option. After you finish the upgrade - including'
            ' all required manual post-upgrade steps as well -'
            '  update to the newer minor version using the dnf tool. In case of using Red Hat'
            ' subscription-manager, do not forget to change the lock version to the newer one'
            ' or unset the version lock before using DNF to be able to perform the minor version update.'
            ' You can use e.g. `subscription-manager release --unset` command for that.'
            .format(get_target_version())
        )),
    ])


def process():
    """
    Check whether the upgrade path will use a target kernel compatible with the source bootloader on ARM systems
    """

    if not matches_architecture(ARCH_ARM64):
        api.current_logger().info('Architecture not ARM. Skipping bootloader check.')
        return

    if matches_target_version('< 9.5'):
        api.current_logger().info((
            'Upgrade on ARM architecture on a compatible path ({} to {}). '
            'Skipping bootloader check.').format(get_source_version(), get_target_version()))
        return

    _inhibit_upgrade()
