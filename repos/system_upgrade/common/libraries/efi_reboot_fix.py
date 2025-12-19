import os
from re import compile as regexp

from leapp.libraries.common import efi
from leapp.libraries.stdlib import api, run

_current_boot_matcher = regexp(r'BootCurrent: (?P<boot_current>([0-9A-F]*))')
_next_boot_matcher = regexp(r'BootNext: (?P<boot_next>([0-9A-F]*))')


def get_current_boot_match(string):
    match = _current_boot_matcher.match(string)
    if not match:
        return None
    captured_groups = match.groupdict()
    return captured_groups['boot_current']


def get_next_boot_match(string):
    match = _next_boot_matcher.match(string)
    if not match:
        return None
    captured_groups = match.groupdict()
    return captured_groups['boot_next']


def maybe_emit_updated_boot_entry():
    if not os.path.exists('/sbin/efibootmgr'):
        return

    efi_info = run(['/sbin/efibootmgr'], checked=False, split=True)
    if efi_info['exit_code'] != 0:
        # Not an efi system
        return

    current_boot, next_boot = None, None
    for line in efi_info['stdout']:
        current_match = get_current_boot_match(line)
        if current_match:
            current_boot = current_match

        next_match = get_next_boot_match(line)
        if next_match:
            next_boot = next_match

    # TODO this only works if the entry with the boot number of BootCurrent
    # wasn't modified.
    # This would happen for example during conversion where the original boot
    # entry is replaced by the one for the target distro, the only thing
    # preventing this is that we set BootNext to the new entry's number.
    #
    # For a proper solution an earlier actor should scan
    # output of `efibootmgr` and produce a message so that we can check that
    # the original entry at BootCurrent wasn't modified.
    if current_boot and not next_boot:
        # We set BootNext to CurrentBoot only if BootNext wasn't previously set
        try:
            efi.set_bootnext(current_boot)
        except efi.EFIError as e:
            api.current_logger().error(
                "Failed to set BootNext to {}: {}".format(current_boot, e)
            )
