from leapp.models import BootEntry, SourceBootLoaderConfiguration
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.exceptions import StopActorExecutionError


CMD_GRUBBY_INFO_ALL = ['grubby', '--info', 'ALL']


def scan_boot_entries():
    """
    Scans the available boot entries.

    :rtype: list
    :returns: A list of available boot entries found in the boot loader configuration.
    """
    try:
        grubby_output = run(CMD_GRUBBY_INFO_ALL, split=True)
    except CalledProcessError as err:
        # We have failed to call `grubby` - something is probably wrong here.
        raise StopActorExecutionError(
            message='Failed to call `grubby` to list available boot entries.',
            details={
                'details': str(err),
                'stderr': err.stderr
            }
        )

    boot_entries = []
    # Identify the available boot entries by searching for their titles in the grubby output
    for output_line in grubby_output['stdout']:
        # For now it is sufficient to look only for the titles as that is the only
        # information we use. If need be, we would have to parse the structure
        # of the grubby output into sections according to the `index` lines
        if output_line.startswith('title='):
            boot_entry = output_line[6:]  # Remove the `title=` prefix

            # On s390x grubby produces quotes only when needed (whitespace in
            # the configuration values), on x86 the values are quoted either way
            boot_entry = boot_entry.strip('\'"')

            boot_entries.append(BootEntry(title=boot_entry))

    return boot_entries


def scan_source_boot_loader_configuration():
    """
    Scans the boot loader configuration.

    Produces :class:`SourceBootLoaderConfiguration for other actors to act upon.
    """

    boot_loader_configuration = SourceBootLoaderConfiguration(
        entries=scan_boot_entries()
    )

    api.produce(boot_loader_configuration)
