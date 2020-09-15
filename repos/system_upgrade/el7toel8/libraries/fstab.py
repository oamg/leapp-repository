from leapp.exceptions import LeappRuntimeError


REMOVED_XFS_OPTIONS = (
    # removed from kernel in 4.0
    'nodelaylog',
    'delaylog',
    'ihashsize',
    'irixsgid',
    'osyncisdsync',
    'osyncisosync',
    # removed from kernel in 4.19
    'nobarrier',
    'barrier',
)


def drop_xfs_options(lines):
    """
    Drop XFS mount options that have been removed in RHEL 8 from contents of /etc/fstab.

    :param lines: A list of lines with the contents of /etc/fstab.
    :return: A modified list of lines with the new contents of /etc/fstab.
    """
    out = list(lines)
    for line in range(len(out)):  # pylint: disable=consider-using-enumerate,too-many-nested-blocks
        if out[line].strip() and out[line][0] != '#':  # line is not blank or a comment
            fields = out[line].split()
            if fields[2] == 'xfs':
                for option in REMOVED_XFS_OPTIONS:
                    # The options can appear with a comma before/after them.
                    # In a valid fstab, any of the options can't appear alone.
                    if option in out[line]:
                        if option + ',' in out[line]:
                            # remove last occurence in string
                            out[line] = ''.join(out[line].rsplit(option + ',', 1))
                        elif ',' + option in out[line]:
                            out[line] = ''.join(out[line].rsplit(',' + option, 1))
                        else:
                            raise LeappRuntimeError(
                                '/etc/fstab: cannot remove option "{}" at line {}'.format(option, line))
    return out
