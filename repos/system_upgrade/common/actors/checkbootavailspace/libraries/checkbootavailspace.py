from __future__ import division

import os
from os import statvfs

from leapp import reporting
from leapp.libraries.stdlib import api

MIN_AVAIL_BYTES_FOR_BOOT = 100 * 2**20  # 100 MiB


def check_avail_space_on_boot(boot_avail_space_getter):
    avail_bytes = boot_avail_space_getter()
    if is_additional_space_required(avail_bytes):
        inhibit_upgrade(avail_bytes)


def get_leftover_upgrade_boot_files():
    """
    Get the leapp upgrade kernel, initramfs and kernel HMAC files left in /boot.

    These files stay in /boot when a previous upgrade attempt failed before
    the RemoveBootFiles actor could remove them.

    :returns: Paths of the files that exist.
    :rtype: List[str]
    """
    arch = api.current_actor().configuration.architecture
    kernel = 'vmlinuz-upgrade.{}'.format(arch)
    names = (kernel, 'initramfs-upgrade.{}.img'.format(arch), '.{}.hmac'.format(kernel))
    paths = [os.path.join('/boot', name) for name in names]
    return [path for path in paths if os.path.isfile(path)]


def get_avail_bytes_on_boot():
    boot_stat = statvfs('/boot')
    avail_bytes = boot_stat.f_frsize * boot_stat.f_bavail
    # The upgrade overwrites these files when it copies the new kernel and
    # initramfs to /boot, so the space they use is available for the upgrade.
    for path in get_leftover_upgrade_boot_files():
        api.current_logger().info(
            'Counting the space used by {} from a previous upgrade attempt as available.'.format(path)
        )
        avail_bytes += os.path.getsize(path)
    return avail_bytes


def is_additional_space_required(avail_bytes):
    return avail_bytes < MIN_AVAIL_BYTES_FOR_BOOT


def inhibit_upgrade(avail_bytes):
    additional_mib_needed = (MIN_AVAIL_BYTES_FOR_BOOT - avail_bytes) / 2**20
    # we use "reporting.report_generic" to allow mocking in the tests
    # WIP ^^ check if this still applies
    reporting.create_report([
        reporting.Title('Not enough space on /boot'),
        reporting.Summary(
            '/boot needs additional {0} MiB to be able to accommodate the upgrade initramfs and new kernel.'.format(
             additional_mib_needed)
        ),
        reporting.ExternalLink(
            url='https://access.redhat.com/solutions/298263',
            title='Why does kernel cannot be upgraded due to insufficient space in /boot ?'
        ),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.FILESYSTEM]),
        reporting.Groups([reporting.Groups.INHIBITOR]),
        reporting.RelatedResource('directory', '/boot')
    ])
