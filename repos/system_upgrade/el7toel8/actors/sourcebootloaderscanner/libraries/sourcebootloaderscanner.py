from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import BootEntry, SourceBootLoaderConfiguration

CMD_GRUBBY_INFO_ALL = ['grubby', '--info', 'ALL']


def parse_grubby_output_line(line):
    """
    Parses a single output line of `grubby --info ALL` that has the property=value format and returns a tuple
    (property, value).

    Quotes are removed from the value.
    :param str line: A line of the grubby output.
    :returns: Tuple containing the key (boot entry property) and its value.
    :rtype: tuple
    """
    line_fragments = line.split('=', 1)
    if len(line_fragments) != 2:
        # The line does not have the property=value format, something is wrong
        raise StopActorExecutionError(
            message='Failed to parse `grubby` output.',
            details={
                'details': 'The following line does not appear to have expected format: {0}'.format(line)
            }
        )

    prop, value = line_fragments
    value = value.strip('\'"')
    return (prop, value)


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
    boot_entry_data = {}
    for output_line in grubby_output['stdout']:
        if output_line == 'non linux entry':
            # Grubby does not display info about non-linux entries
            # Such an entry is not problematic from our PoV, therefore, skip it
            boot_entry_data = {}
            continue

        prop, value = parse_grubby_output_line(output_line)
        if prop == 'index':
            # Start of a new boot entry section
            if boot_entry_data:
                # There has been a valid linux entry
                boot_entries.append(
                    BootEntry(title=boot_entry_data.get('title', ''),  # In theory, the title property can be missing
                              kernel_image=boot_entry_data['kernel']))
            boot_entry_data = {}
        boot_entry_data[prop] = value

    # There was no 'index=' line after the last boot entry section, thus, its data has not been converted to a model.
    if boot_entry_data:
        boot_entries.append(BootEntry(title=boot_entry_data.get('title', ''),
                                      kernel_image=boot_entry_data['kernel']))
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
