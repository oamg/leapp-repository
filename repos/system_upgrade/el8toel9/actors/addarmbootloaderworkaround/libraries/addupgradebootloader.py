import os
import tempfile
import shutil
import glob

from leapp.libraries.stdlib import CalledProcessError
from leapp.models import TargetUserSpaceInfo
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import mounting
from leapp.libraries.stdlib import api, run
from leapp.libraries.common.grub import (EFIBootInfo,
                                         get_efi_partition, get_blk_device, get_efi_partition, get_device_number)

ARM_SHIM_PACKAGE_NAME = 'shim-aa64'
ARM_GRUB_PACKAGE_NAME = 'grub2-efi-aa64'

EFI_MOUNTPOINT = '/boot/efi/'
LEAPP_EFIDIR_CANONICAL_PATH = os.path.join(EFI_MOUNTPOINT, 'EFI/leapp/')
RHEL_EFIDIR_CANONICAL_PATH = os.path.join(EFI_MOUNTPOINT, 'EFI/redhat/')


def get_efi_device():
    """Get the block device on which GRUB is installed."""

    return get_blk_device(get_efi_partition())


def canonical_path_to_efi_format(canonical_path):
    r"""Transform the canonical path to the UEFI format.

    e.g. /boot/efi/EFI/redhat/shimx64.efi -> \EFI\redhat\shimx64.efi
    (just single backslash; so the string needs to be put into apostrophes
    when used for /usr/sbin/efibootmgr cmd)

    The path has to start with /boot/efi otherwise the path is invalid for UEFI.
    """

    # We want to keep the last "/" of the EFI_MOUNTPOINT
    return canonical_path.replace(EFI_MOUNTPOINT[:-1], "").replace("/", "\\")


def _get_upgrade_boot_entry(efibootinfo, efi_path, label):
    for entry in efibootinfo.entries.values():
        if entry.label == label and efi_path in entry.efi_bin_source:
            return entry

    return None


def _is_upgrade_in_boot_entries(efibootinfo, efi_path, label):
    return _get_upgrade_boot_entry(efibootinfo, efi_path, label) is not None


def _set_bootnext(boot_number):
    result = run(['efibootmgr', '-n', boot_number], checked=False)
    if result['exit_code']:
        raise StopActorExecutionError('Could not set Leapp upgrade boot entry as BootNext.')


def _add_upgrade_boot_entry():
    """
    Create a new UEFI bootloader entry with a RHEL label and bin file.

    If an entry for the label and bin file already exists no new entry
    will be created.

    Return the new bootloader info (EFIBootInfo).
    """

    dev_number = get_device_number(get_efi_partition())
    blk_dev = get_efi_device()

    tmp_efi_path = os.path.join(LEAPP_EFIDIR_CANONICAL_PATH, 'shimaa64.efi')
    if os.path.exists(tmp_efi_path):
        efi_path = canonical_path_to_efi_format(tmp_efi_path)
    else:
        raise StopActorExecutionError(
            'Unable to detect upgrade UEFI binary file.')

    label = 'Leapp Upgrade'

    efibootinfo = EFIBootInfo()
    if _is_upgrade_in_boot_entries(efibootinfo, efi_path, label):
        return efibootinfo

    # NOTE: The new boot entry is being set as first in the boot order
    cmd = [
        "/usr/sbin/efibootmgr",
        "--create",
        "--disk",
        blk_dev,
        "--part",
        str(dev_number),
        "--loader",
        efi_path,
        "--label",
        label,
    ]

    result = run(cmd, checked=False)
    if result['exit_code']:
        raise StopActorExecutionError(
            'Unable to add a new UEFI bootloader entry for Leapp upgrade.')

    # Sanity check boot entry has been added
    efibootinfo_new = EFIBootInfo()
    if _is_upgrade_in_boot_entries(efibootinfo_new, efi_path, label):
        raise StopActorExecutionError(
            'Unable to find the new UEFI bootloader entry after adding.')

    return efibootinfo_new


def process():
    userspace = next(api.consume(TargetUserSpaceInfo), None)

    # TODO(dkubek): Sanity check we obtained the userspace
    assert userspace is not None

    binds = ['/boot', '/dev']
    with mounting.NspawnActions(base_dir=userspace.path, binds=binds) as context:

        # Ensure clean environment
        if os.path.exists(LEAPP_EFIDIR_CANONICAL_PATH):
            shutil.rmtree(LEAPP_EFIDIR_CANONICAL_PATH)

        # Create directory /boot/efi/EFI/leapp
        os.mkdir(LEAPP_EFIDIR_CANONICAL_PATH)

        # Download packages
        with tempfile.TemporaryDirectory() as tmpdir:
            for package_name in (ARM_SHIM_PACKAGE_NAME, ARM_GRUB_PACKAGE_NAME):
                container_tmpdir = '/tmp_pkg_download_dir'

                # Download the package rpm and rename it
                context.call(['dnf', 'download', '-y', '--downloaddir', container_tmpdir, package_name,
                              # TODO: BIG HACK, figure out how to best handle this
                              '--setopt=module_platform_id=platform:el9',
                              '--setopt=keepcache=1', '--releasever', '9.5',
                              '--disablerepo', '*',
                              '--enablerepo', 'BASEOS', '--enablerepo', 'APPSTREAM'])

                package_glob = os.path.join(context.full_path(container_tmpdir), package_name + '*')
                result = glob.glob(package_glob)
                assert len(result) == 1
                rpm_name = os.path.basename(result[0])
                if not rpm_name:
                    raise StopActorExecutionError('Could not resolve rpm name of {}'.format(package_name))

                # Copy the package to the host
                host_dir = os.path.join(tmpdir, package_name)
                os.mkdir(host_dir)
                context.copy_from(os.path.join(container_tmpdir, rpm_name), host_dir)

                # Cleanup in the container
                context.remove_tree(container_tmpdir)

                # Extract files from boot/efi/EFI/
                # FIXME: Add error checking
                package_path = os.path.join(host_dir, rpm_name)
                run(['rpm2archive', package_path])
                run([
                    'tar',
                    '--gzip',
                    '--extract',
                    '--file',
                    package_path + '.tgz',
                    '--directory={}'.format(host_dir),
                    '--verbose',  # For logging and debugging
                ],
                )

                # Copy required files to LEAPP_EFIDIR_CANONICAL_PATH
                run(['cp', '-r', os.path.join(host_dir, RHEL_EFIDIR_CANONICAL_PATH, '.'), LEAPP_EFIDIR_CANONICAL_PATH])

        # TODO: Copy grub.cfg and grubenv

        # Create efi entry and set it as default
        efibootinfo = _add_upgrade_boot_entry()

        upgrade_boot_entry = _get_upgrade_boot_entry(efibootinfo, efi_path, label)
        _set_bootnext(upgrade_boot_entry.boot_number)
