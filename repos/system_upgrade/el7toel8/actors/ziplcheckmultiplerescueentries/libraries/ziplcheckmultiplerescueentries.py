from leapp import reporting
from leapp.libraries.common.config import architecture

FMT_LIST_SEPARATOR = '\n    - '


def inhibit_if_multiple_zipl_rescue_entries_present(bootloader_config):
    """
    Inhibits the upgrade if we are running on s390x and the bootloader configuration
    contains multiple rescue boot entries.

    A boot entry is recognized as a rescue entry when its title contains the `rescue` substring.

    :param SourceBootloaderConfiguration bootloader_config: The configuration of the source boot loader.
    """

    if not architecture.matches_architecture(architecture.ARCH_S390X):
        # Zipl is used only on s390x
        return

    # Keep the whole information about boot entries not just their count as
    # we want to provide user with the details
    rescue_entries = []
    for boot_entry in bootloader_config.entries:
        if 'rescue' in boot_entry.title.lower():
            rescue_entries.append(boot_entry)

    if len(rescue_entries) > 1:
        # Prepare the list of available rescue entries for user
        rescue_entries_text = ''
        for rescue_entry in rescue_entries:
            rescue_entries_text += '{0}{1}'.format(FMT_LIST_SEPARATOR, rescue_entry.title)
        zipl_config_path = '/etc/zipl.conf'

        reporting.create_report([
            reporting.Title('Multiple rescue boot entries present in the bootloader configuration.'),
            reporting.Summary(
                'The zipl configuration file {0} contains multiple rescue boot entries:{1}'
                .format(zipl_config_path, rescue_entries_text)
            ),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Tags([reporting.Tags.BOOT]),
            reporting.Remediation(hint='Remove rescue boot entries from the configuration and leave just one.'),
            reporting.Flags([reporting.Flags.INHIBITOR])
        ])
