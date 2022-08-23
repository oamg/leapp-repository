from collections import defaultdict

from leapp import reporting
from leapp.libraries.common.config import architecture

FMT_LIST_SEPARATOR = '\n    - '
ZIPL_CONFIG_PATH = '/etc/zipl.conf'


def is_rescue_entry(boot_entry):
    """
    Determines whether the given boot entry is rescue.

    :param BootEntry boot_entry: Boot entry to assess
    :return: True is the entry is rescue
    :rtype:  bool
    """
    return 'rescue' in boot_entry.kernel_image.lower()


def inhibit_if_multiple_zipl_rescue_entries_present(bootloader_config):
    """
    Inhibits the upgrade if we are running on s390x and the bootloader configuration
    contains multiple rescue boot entries.

    A boot entry is recognized as a rescue entry when its title contains the `rescue` substring.

    :param SourceBootloaderConfiguration bootloader_config: The configuration of the source boot loader.
    """

    # Keep the whole information about boot entries not just their count as
    # we want to provide user with the details
    rescue_entries = []
    for boot_entry in bootloader_config.entries:
        if is_rescue_entry(boot_entry):
            rescue_entries.append(boot_entry)

    if len(rescue_entries) > 1:
        # Prepare the list of available rescue entries for user
        rescue_entries_text = ''
        for rescue_entry in rescue_entries:
            rescue_entries_text += '{0}{1}'.format(FMT_LIST_SEPARATOR, rescue_entry.title)

        summary = ('The Zipl configuration file {0} contains multiple rescue boot entries preventing migration '
                   'to BLS. Problematic entries: {1}')

        reporting.create_report([
            reporting.Title('Multiple rescue boot entries present in the bootloader configuration.'),
            reporting.Summary(summary.format(ZIPL_CONFIG_PATH, rescue_entries_text)),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.BOOT]),
            reporting.Remediation(hint='Remove rescue boot entries from the configuration and leave just one.'),
            reporting.Groups([reporting.Groups.INHIBITOR])
        ])


def extract_kernel_version(kernel_img_path):
    """
    Extracts the kernel version out of the given image path.

    The extraction logic is designed to closely mimic the logic Zipl configuration to BLS
    conversion script works, so that it is possible to identify the possible issues with kernel
    images.

    :param str kernel_img_path: The path to the kernel image.
    :returns: Extracted kernel version from the given path
    :rtype: str
    """

    # Mimic bash substitution used in the conversion script, see:
    # https://github.com/ibm-s390-linux/s390-tools/blob/b5604850ab66f862850568a37404faa647b5c098/scripts/zipl-switch-to-blscfg#L168
    if 'vmlinuz-' in kernel_img_path:
        fragments = kernel_img_path.rsplit('/vmlinuz-', 1)
        return fragments[1] if len(fragments) > 1 else fragments[0]

    fragments = kernel_img_path.rsplit('/', 1)
    return fragments[1] if len(fragments) > 1 else fragments[0]


def inhibit_if_entries_share_kernel_version(bootloader_config):
    """
    Inhibits the upgrade if there are boot entries sharing the same kernel image version.

    The logic of identification whether the images are the same mimics the zipl-switch-to-blscfg, as it fails
    to perform the conversion if there are entries with the same kernel image.

    :param SourceBootloaderConfiguration bootloader_config: The configuration of the source boot loader.
    """

    used_kernel_versions = defaultdict(list)  # Maps images to the boot entries in which they are used
    for boot_entry in bootloader_config.entries:
        if is_rescue_entry(boot_entry):
            # Rescue entries are handled differently and their images should not cause naming collisions
            continue

        kernel_version = extract_kernel_version(boot_entry.kernel_image)
        used_kernel_versions[kernel_version].append(boot_entry)

    versions_used_multiple_times = []
    for version, version_boot_entries in used_kernel_versions.items():
        if len(version_boot_entries) > 1:
            # Keep the information about entries for the report
            versions_used_multiple_times.append((version, version_boot_entries))

    if versions_used_multiple_times:
        problematic_entries_details = ''
        for version, version_boot_entries in versions_used_multiple_times:
            entry_titles = ['"{0}"'.format(entry.title) for entry in version_boot_entries]
            problematic_entries_details += '{0}{1} (found in entries: {2})'.format(
                    FMT_LIST_SEPARATOR,
                    version,
                    ', '.join(entry_titles)
            )

        summary = ('The zipl configuration file {0} contains boot entries sharing the same kernel version '
                   'preventing migration to BLS. Kernel versions shared: {1}')
        reporting.create_report([
            reporting.Title('Boot entries sharing the same kernel version found.'),
            reporting.Summary(summary.format(ZIPL_CONFIG_PATH, problematic_entries_details)),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.BOOT]),
            reporting.Remediation(
                hint='Remove boot entries sharing the same kernel version from the configuration and leave just one.'),
            reporting.Groups([reporting.Groups.INHIBITOR])
        ])


def inhibit_if_invalid_zipl_configuration(bootloader_config):
    if not architecture.matches_architecture(architecture.ARCH_S390X):
        # Zipl is used only on s390x
        return

    inhibit_if_multiple_zipl_rescue_entries_present(bootloader_config)
    inhibit_if_entries_share_kernel_version(bootloader_config)
