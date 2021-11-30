import os
from re import compile as regexp

from leapp.libraries.stdlib import run

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

    if current_boot and not next_boot:
        # We set BootNext to CurrentBoot only if BootNext wasn't previously set
        run(['/sbin/efibootmgr', '-n', current_boot])
