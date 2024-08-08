import os
import tempfile
import shutil
import glob

from leapp.libraries.stdlib import CalledProcessError
from leapp.models import TargetUserSpaceInfo, EFIBootEntry, ArmWorkaroundEFIBootloaderInfo
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import mounting
from leapp.libraries.stdlib import api, run
from leapp.libraries.common.grub import (EFIBootInfo, get_blk_device, get_efi_partition, get_device_number,
                                         canonical_path_to_efi_format, get_efi_device, GRUB2_BIOS_ENV_FILE, GRUB2_BIOS_ENTRYPOINT)

UPGRADE_EFI_ENTRY_LABEL = 'Leapp Upgrade'

ARM_SHIM_PACKAGE_NAME = 'shim-aa64'
ARM_GRUB_PACKAGE_NAME = 'grub2-efi-aa64'

EFI_MOUNTPOINT = '/boot/efi/'
LEAPP_EFIDIR_CANONICAL_PATH = os.path.join(EFI_MOUNTPOINT, 'EFI/leapp/')
RHEL_EFIDIR_CANONICAL_PATH = os.path.join(EFI_MOUNTPOINT, 'EFI/redhat/')

CONTAINER_DOWNLOAD_DIR = '/tmp_pkg_download_dir'


def _copy_file(src_path, dst_path):
    if os.path.exists(dst_path):
        api.current_logger().debug("The {} file already exists and its content will be overwritten.".format(dst_path))

    api.current_logger().info("Copying {} to {}".format(src_path, dst_path))
    try:
        shutil.copy2(src_path, dst_path)
    except (OSError, IOError) as err:
        raise StopActorExecutionError('I/O error({}): {}'.format(err.errno, err.strerror))


def process():
    userspace = _get_userspace_info()

    binds = ['/boot', '/dev']
    with mounting.NspawnActions(base_dir=userspace.path, binds=binds) as context:
        _ensure_clean_environment()

        # Download packages
        for package_name in (ARM_SHIM_PACKAGE_NAME, ARM_GRUB_PACKAGE_NAME):
            with tempfile.TemporaryDirectory() as tmpdir:
                rpm_path = _download_package_to_container(context, package_name)

                _copy_file(context.full_path(rpm_path), tmpdir)

                _cleanup_container(context)

                rpm_name = os.path.basename(rpm_path)
                package_path = os.path.join(tmpdir, rpm_name)
                _extract_package_files(package_path, tmpdir)

                rhel_boot_files_dir = os.path.join(tmpdir, RHEL_EFIDIR_CANONICAL_PATH.lstrip(os.path.sep))
                _copy_directory_content(rhel_boot_files_dir, LEAPP_EFIDIR_CANONICAL_PATH)

        _copy_grub_files(['grubenv', 'grub.cfg'], ['user.cfg'])
        _link_grubenv_to_upgrade_entry()

        efibootinfo = EFIBootInfo()
        current_boot_entry = efibootinfo.entries[efibootinfo.current_bootnum]
        upgrade_boot_entry = _add_upgrade_boot_entry(efibootinfo)
        _set_bootnext(upgrade_boot_entry.boot_number)

        efibootentry_fields = ['boot_number', 'label', 'active', 'efi_bin_source']
        api.produce(
            ArmWorkaroundEFIBootloaderInfo(
                original_entry=EFIBootEntry(**{f: getattr(current_boot_entry, f) for f in efibootentry_fields}),
                upgrade_entry=EFIBootEntry(**{f: getattr(upgrade_boot_entry, f) for f in efibootentry_fields}),
            )
        )


def _get_userspace_info():
    msgs = api.consume(TargetUserSpaceInfo)

    userspace = next(msgs, None)
    if userspace is None:
        raise StopActorExecutionError(
            'Could not retrieve TargetUserSpaceInfo!')

    if next(msgs, None):
        raise api.current_logger().warning(
            'Unexpectedly received more than one TargetUserSpaceInfo message.')

    return userspace


def _ensure_clean_environment():
    if os.path.exists(LEAPP_EFIDIR_CANONICAL_PATH):
        shutil.rmtree(LEAPP_EFIDIR_CANONICAL_PATH)

    os.mkdir(LEAPP_EFIDIR_CANONICAL_PATH)


def _download_package_to_container(context, package_name):

    _run_dnf_download(context, package_name)
    rpm_path = _get_rpm_path(context, package_name)

    return rpm_path


def _run_dnf_download(context, package_name):
    api.current_logger().debug("Downloading package {}".format(package_name))
    context.call(['dnf', 'download', '-y', '--downloaddir', CONTAINER_DOWNLOAD_DIR, package_name,
                  '--setopt=module_platform_id=platform:el9',
                  # FIXME: Hardcoded for now
                  '--releasever', '9.5',
                  '--disablerepo', '*',
                  '--enablerepo', 'BASEOS', '--enablerepo', 'APPSTREAM'])


def _get_rpm_path(context, package_name):

    package_path_glob = os.path.join(context.full_path(CONTAINER_DOWNLOAD_DIR), package_name + '*')
    result = glob.glob(package_path_glob)
    if len(result) < 1:
        msg = 'Could not find the RPM of package {} in container environment!'.format(package_name)
        api.current_logger().error(msg)
        raise StopActorExecutionError(msg)

    if len(result) > 1:
        msg = 'Globbing for package returned multiple results!'
        api.current_logger().error(msg + " Found: {}".format(result))
        raise StopActorExecutionError(msg)

    rpm_name = os.path.basename(result[0])
    if not rpm_name:
        raise StopActorExecutionError('Could not resolve RPM name of {}'.format(package_name))

    return os.path.join(CONTAINER_DOWNLOAD_DIR, rpm_name)


def _cleanup_container(context):
    context.remove_tree(CONTAINER_DOWNLOAD_DIR)


def _extract_package_files(package_path, out_directory):
    run(['rpm2archive', package_path])
    run([
        'tar',
        '--gzip',
        '--extract',
        '--file',
        package_path + '.tgz',
        '--directory={}'.format(out_directory),
        '--verbose',
    ])


def _copy_directory_content(src_dir, dst_dir):
    run(['cp', '--recursive', os.path.join(src_dir, '.'), dst_dir])


def _copy_grub_files(required, optional):
    """
    Copy grub files from redhat/ dir to the /boot/efi/EFI/leapp/ dir.
    """

    all_files = required + optional
    for filename in all_files:
        src_path = os.path.join(RHEL_EFIDIR_CANONICAL_PATH, filename)
        dst_path = os.path.join(LEAPP_EFIDIR_CANONICAL_PATH, filename)

        if not os.path.exists(src_path):
            if filename in required:
                msg = 'Required file {} does not exists. Aborting.'.format(filename)
                raise StopActorExecutionError(msg)

            continue

        _copy_file(src_path, dst_path)


def _link_grubenv_to_upgrade_entry():
    upgrade_env_file = os.path.join(LEAPP_EFIDIR_CANONICAL_PATH, 'grubenv')
    upgrade_env_file_relpath = os.path.relpath(upgrade_env_file, GRUB2_BIOS_ENTRYPOINT)
    run(['ln', '--symbolic', '--force', upgrade_env_file_relpath, GRUB2_BIOS_ENV_FILE])


def _add_upgrade_boot_entry(efibootinfo):
    """
    Create a new UEFI bootloader entry with a upgrade label and bin file.

    If an entry for the label and bin file already exists no new entry
    will be created.

    Return the upgrade efi entry (EFIEntry).
    """

    dev_number = get_device_number(get_efi_partition())
    blk_dev = get_efi_device()

    tmp_efi_path = os.path.join(LEAPP_EFIDIR_CANONICAL_PATH, 'shimaa64.efi')
    if os.path.exists(tmp_efi_path):
        efi_path = canonical_path_to_efi_format(tmp_efi_path)
    else:
        raise StopActorExecutionError('Unable to detect upgrade UEFI binary file.')

    upgrade_boot_entry = _get_upgrade_boot_entry(efibootinfo, efi_path, UPGRADE_EFI_ENTRY_LABEL)
    if upgrade_boot_entry is not None:
        return upgrade_boot_entry

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
        UPGRADE_EFI_ENTRY_LABEL,
    ]

    result = run(cmd, checked=False)
    if result['exit_code']:
        raise StopActorExecutionError('Unable to add a new UEFI bootloader entry for upgrade.')

    # Sanity check new boot entry has been added
    efibootinfo_new = EFIBootInfo()
    upgrade_boot_entry = _get_upgrade_boot_entry(efibootinfo_new, efi_path, UPGRADE_EFI_ENTRY_LABEL)
    if upgrade_boot_entry is None:
        raise StopActorExecutionError('Unable to find the new UEFI bootloader entry after adding it.')

    return upgrade_boot_entry


def _get_upgrade_boot_entry(efibootinfo, efi_path, label):
    """
    Get the UEFI boot entry with label `label` and EFI binary path `efi_path`

    Return EFIBootEntry or None if not found.
    """

    for entry in efibootinfo.entries.values():
        if entry.label == label and efi_path in entry.efi_bin_source:
            return entry

    return None


def _set_bootnext(boot_number):
    """
    Set the BootNext UEFI entry to `boot_number`.
    """

    api.current_logger().debug('Setting {} as BootNext'.format(boot_number))
    result = run(['/usr/sbin/efibootmgr', '--bootnext', boot_number], checked=False)
    if result['exit_code']:
        raise StopActorExecutionError('Could not set boot entry {} as BootNext.'.format(boot_number))
