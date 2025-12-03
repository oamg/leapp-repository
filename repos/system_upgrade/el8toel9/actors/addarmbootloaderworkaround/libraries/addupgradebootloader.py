import os
import shutil

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import mounting
from leapp.libraries.common.firmware import efi
from leapp.libraries.common.grub import get_boot_partition
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import ArmWorkaroundEFIBootloaderInfo, EFIBootEntry, TargetUserSpaceInfo

UPGRADE_EFI_ENTRY_LABEL = 'Leapp Upgrade'

ARM_SHIM_PACKAGE_NAME = 'shim-aa64'
ARM_GRUB_PACKAGE_NAME = 'grub2-efi-aa64'

LEAPP_EFIDIR_CANONICAL_PATH = os.path.join(efi.EFI_MOUNTPOINT, 'EFI/leapp/')
RHEL_EFIDIR_CANONICAL_PATH = os.path.join(efi.EFI_MOUNTPOINT, 'EFI/redhat/')
UPGRADE_BLS_DIR = '/boot/upgrade-loader'

CONTAINER_DOWNLOAD_DIR = '/tmp_pkg_download_dir'

LEAPP_GRUB2_CFG_TEMPLATE = 'grub2_config_template'
"""
Our grub configuration file template that is used in case the system's grubcfg would not load our grubenv.

The template contains placeholders named with LEAPP_*, that need to be replaced in order to
obtain a valid config.

"""


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

    with mounting.NspawnActions(base_dir=userspace.path) as context:
        _ensure_clean_environment()

        # NOTE(dkubek): Assumes required shim-aa64 and grub2-efi-aa64 packages
        # have been installed
        context.copytree_from(RHEL_EFIDIR_CANONICAL_PATH, LEAPP_EFIDIR_CANONICAL_PATH)

        _copy_grub_files(['grubenv', 'grub.cfg'], ['user.cfg'])

        efibootinfo = efi.EFIBootInfo()
        current_boot_entry = efibootinfo.entries[efibootinfo.current_bootnum]
        upgrade_boot_entry = _add_upgrade_boot_entry(efibootinfo)

        patch_efi_redhat_grubcfg_to_load_correct_grubenv()

        efi.set_bootnext(upgrade_boot_entry.boot_number)

        efibootentry_fields = ['boot_number', 'label', 'active', 'efi_bin_source']
        api.produce(
            ArmWorkaroundEFIBootloaderInfo(
                original_entry=EFIBootEntry(**{f: getattr(current_boot_entry, f) for f in efibootentry_fields}),
                upgrade_entry=EFIBootEntry(**{f: getattr(upgrade_boot_entry, f) for f in efibootentry_fields}),
                upgrade_bls_dir=UPGRADE_BLS_DIR,
                upgrade_entry_efi_path=os.path.join(efi.EFI_MOUNTPOINT, LEAPP_EFIDIR_CANONICAL_PATH),
            )
        )


def _get_userspace_info():
    msgs = api.consume(TargetUserSpaceInfo)

    userspace = next(msgs, None)
    if userspace is None:
        raise StopActorExecutionError('Could not retrieve TargetUserSpaceInfo!')

    if next(msgs, None):
        api.current_logger().warning('Unexpectedly received more than one TargetUserSpaceInfo message.')

    return userspace


def _ensure_clean_environment():
    if os.path.exists(LEAPP_EFIDIR_CANONICAL_PATH):
        shutil.rmtree(LEAPP_EFIDIR_CANONICAL_PATH)


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


def _add_upgrade_boot_entry(efibootinfo):
    """
    Create a new UEFI bootloader entry with a upgrade label and bin file.

    If an entry for the label and bin file already exists no new entry
    will be created.

    Return the upgrade efi entry (EFIEntry).
    """

    tmp_efi_path = os.path.join(LEAPP_EFIDIR_CANONICAL_PATH, 'shimaa64.efi')
    if os.path.exists(tmp_efi_path):
        efi_path = efi.canonical_path_to_efi_format(tmp_efi_path)
    else:
        raise StopActorExecutionError('Unable to detect upgrade UEFI binary file.')

    upgrade_boot_entry = efi.get_boot_entry(efibootinfo, efi_path, UPGRADE_EFI_ENTRY_LABEL)
    if upgrade_boot_entry is not None:
        return upgrade_boot_entry

    try:
        return efi.add_boot_entry(UPGRADE_EFI_ENTRY_LABEL, efi_path)
    except efi.EFIError as e:
        raise StopActorExecutionError(
            "Unable to add a new UEFI bootloader entry for upgrade: {}"
        ) from e


def _notify_user_to_check_grub2_cfg():
    # Or maybe rather ask a question in a dialog? But this is rare, so maybe continuing is fine.
    pass


def _will_grubcfg_read_our_grubenv(grubcfg_path):
    with open(grubcfg_path) as grubcfg:
        config_lines = grubcfg.readlines()

    will_read = False
    for line in config_lines:
        if line.strip() == 'load_env -f ${config_directory}/grubenv':
            will_read = True
            break

    return will_read


def _get_boot_device_uuid():
    boot_device = get_boot_partition()
    try:
        raw_device_info_lines = run(['blkid', boot_device], split=True)['stdout']
        raw_device_info = raw_device_info_lines[0]  # There is only 1 output line

        uuid_needle_start_pos = raw_device_info.index('UUID')
        raw_device_info = raw_device_info[uuid_needle_start_pos:]  # results in: "UUID="..." ....

        uuid = raw_device_info.split(' ', 1)[0]  # UUID cannot contain spaces
        uuid = uuid[len('UUID='):]  # Remove UUID=
        uuid = uuid.strip('"')
        return uuid

    except CalledProcessError as error:
        details = {'details': 'blkid failed with error: {}'.format(error)}
        raise StopActorExecutionError('Failed to obtain UUID of /boot partition', details=details)


def _prepare_config_contents():
    config_template_path = api.get_actor_file_path(LEAPP_GRUB2_CFG_TEMPLATE)
    with open(config_template_path) as config_template_handle:
        config_template = config_template_handle.read()

    substitutions = {
        'LEAPP_BOOT_UUID': _get_boot_device_uuid()
    }

    api.current_logger().debug(
        'Applying the following substitution map to grub config template: {}'.format(substitutions)
    )

    for placeholder, placeholder_value in substitutions.items():
        config_template = config_template.replace(placeholder, placeholder_value)

    return config_template


def _write_config(config_path, config_contents):
    with open(config_path, 'w') as grub_cfg_handle:
        grub_cfg_handle.write(config_contents)


def patch_efi_redhat_grubcfg_to_load_correct_grubenv():
    """
    Replaces /boot/efi/EFI/redhat/grub2.cfg with a patched grub2.cfg shipped in leapp.

    The grub2.cfg shipped on some AWS images omits the section that loads grubenv different
    EFI entries. Thus, we need to replace it with our own that will load grubenv shipped
    of our UEFI boot entry.
    """
    leapp_grub_cfg_path = os.path.join(LEAPP_EFIDIR_CANONICAL_PATH, 'grub.cfg')

    if not os.path.isfile(leapp_grub_cfg_path):
        msg = 'The file {} does not exists, cannot check whether bootloader is configured properly.'
        raise StopActorExecutionError(msg.format(leapp_grub_cfg_path))

    if _will_grubcfg_read_our_grubenv(leapp_grub_cfg_path):
        api.current_logger().debug('The current grub.cfg will read our grubenv without any modifications.')
        return

    api.current_logger().info('Current grub2.cfg is likely faulty (would not read our grubenv), patching.')

    config_contents = _prepare_config_contents()
    _write_config(leapp_grub_cfg_path, config_contents)

    api.current_logger().info('New upgrade grub.cfg has been written to {}'.format(leapp_grub_cfg_path))
