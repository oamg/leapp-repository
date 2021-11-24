from re import compile as regexp
import os

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

    if current_boot and not next_boot:
        # We set BootNext to CurrentBoot only if BootNext wasn't previously set
        result = run(['/sbin/efibootmgr', '-n', current_boot], checked=False)
        if result['exit_code'] != 0:
            api.current_logger().warning(
                'Cannot set the next boot for EFI. This usually does not affect'
                ' system negatively, but in case the default EFI boot has'
                ' a special effects, the upgrade does not have to be finished'
                ' as expected. It could be problem e.g. for machines in special'
                ' testing infrastructure.'
            )
            api.current_logger().warning('Discovered current boot: {}'.format(current_boot))
            api.current_logger().warning('Original post-upgrade EFI info: {}'.format(efi_info['stdout']))
            new_efi_info = run(['/sbin/efibootmgr'], checked=False, split=True)
            api.current_logger().warning('The EFI info after the error: {}'.format(new_efi_info['stdout']))
