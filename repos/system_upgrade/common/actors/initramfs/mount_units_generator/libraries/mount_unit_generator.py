import os
import shutil
import tempfile

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import mounting
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import LiveModeConfig, StorageInfo, TargetUserSpaceInfo, UpgradeInitramfsTasks

BIND_MOUNT_SYSROOT_BOOT_UNIT = 'boot.mount'


def run_systemd_fstab_generator(output_directory):
    api.current_logger().debug(
        'Generating mount units for the source system into {}'.format(output_directory)
    )

    try:
        generator_cmd = [
            '/usr/lib/systemd/system-generators/systemd-fstab-generator',
            output_directory,
            output_directory,
            output_directory
        ]
        run(generator_cmd)
    except CalledProcessError as error:
        api.current_logger().error(
            'Failed to generate mount units using systemd-fstab-generator. Error: {}'.format(error)
        )
        details = {'details': str(error)}
        raise StopActorExecutionError(
            'Failed to generate mount units using systemd-fstab-generator',
            details
        )

    api.current_logger().debug(
        'Mount units successfully generated into {}'.format(output_directory)
    )


def _read_unit_file_lines(unit_file_path):  # Encapsulate IO for tests
    with open(unit_file_path) as unit_file:
        return unit_file.readlines()


def _write_unit_file_lines(unit_file_path, lines):  # Encapsulate IO for tests
    with open(unit_file_path, 'w') as unit_file:
        unit_file.write('\n'.join(lines) + '\n')


def _delete_file(file_path):
    os.unlink(file_path)


def _prefix_mount_unit_with_sysroot(mount_unit_path, new_unit_destination):
    """
    Prefix the mount target with /sysroot as expected in the upgrade initramfs.

    A new mount unit file is written to new_unit_destination.
    """
    # NOTE(pstodulk): Note that right now we update just the 'Where' key, however
    # what about RequiresMountsFor, .. there could be some hidden dragons.
    # In case of issues, investigate these values in generated unit files.
    api.current_logger().debug(
        'Prefixing {}\'s mount target with /sysroot. Output will be written to {}'.format(
            mount_unit_path,
            new_unit_destination
        )
    )
    unit_lines = _read_unit_file_lines(mount_unit_path)

    output_lines = []
    for line in unit_lines:
        line = line.strip()
        if not line.startswith('Where='):
            output_lines.append(line)
            continue

        _, destination = line.split('=', 1)
        new_destination = os.path.join('/sysroot', destination.lstrip('/'))

        output_lines.append('Where={}'.format(new_destination))

    _write_unit_file_lines(new_unit_destination, output_lines)

    api.current_logger().debug(
        'Done. Modified mount unit successfully written to {}'.format(new_unit_destination)
    )


def prefix_all_mount_units_with_sysroot(dir_containing_units):
    for unit_file_path in os.listdir(dir_containing_units):
        # systemd requires mount path to be in the unit name
        modified_unit_destination = 'sysroot-{}'.format(unit_file_path)
        modified_unit_destination = os.path.join(dir_containing_units, modified_unit_destination)

        unit_file_path = os.path.join(dir_containing_units, unit_file_path)

        if not unit_file_path.endswith('.mount'):
            api.current_logger().debug(
                'Skipping {} when prefixing mount units with /sysroot - not a mount unit.'.format(
                    unit_file_path
                )
            )
            continue

        _prefix_mount_unit_with_sysroot(unit_file_path, modified_unit_destination)

        _delete_file(unit_file_path)
        api.current_logger().debug('Original mount unit {} removed.'.format(unit_file_path))


def _fix_symlinks_in_dir(dir_containing_mount_units, target_dir):
    """
    Fix broken symlinks in given target_dir due to us modifying (renaming) the mount units.

    The target_dir contains symlinks to the (mount) units that are required
    in order for the local-fs.target to be reached. However, we renamed these units to reflect
    that we have changed their mount destinations by prefixing the mount destination with /sysroot.
    Hence, we regenerate the symlinks.
    """

    target_dir_path = os.path.join(dir_containing_mount_units, target_dir)
    if not os.path.exists(target_dir_path):
        api.current_logger().debug(
            'The {} directory does not exist. Skipping'
            .format(target_dir)
        )
        return

    api.current_logger().debug(
        'Removing the old {} directory from {}.'
        .format(target_dir, dir_containing_mount_units)
    )

    shutil.rmtree(target_dir_path)
    os.mkdir(target_dir_path)

    api.current_logger().debug('Populating {} with new symlinks.'.format(target_dir))

    for unit_file in os.listdir(dir_containing_mount_units):
        if not unit_file.endswith('.mount'):
            continue

        place_fastlink_at = os.path.join(target_dir_path, unit_file)
        fastlink_points_to = os.path.join('../', unit_file)
        try:
            run(['ln', '-s', fastlink_points_to, place_fastlink_at])

            api.current_logger().debug(
                'Dependency on {} created.'.format(unit_file)
            )
        except CalledProcessError as err:
            err_descr = (
                'Failed to create required unit dependencies under {} for the upgrade initramfs.'
                .format(target_dir)
            )
            details = {'details': str(err)}
            raise StopActorExecutionError(err_descr, details=details)


def fix_symlinks_in_targets(dir_containing_mount_units):
    """
    Fix broken symlinks in *.target.* directories caused by earlier modified mount units.

    Generated mount unit files are part of one of systemd targets (list below),
    which means that a symlink from a systemd target to exists for each of
    them. Based on this, systemd knows when (local or remote file systems?)
    they must (".requires" suffix") or could (".wants" suffix) be mounted.
    See the man 5 systemd.mount for more details how mount units are split into
    these targets.

    The list of possible target directories where these mount units could end:
        * local-fs.target.requires
        * local-fs.target.wants
        * local-fs-pre.target.requires
        * local-fs-pre.target.wants
        * remote-fs.target.requires
        * remote-fs.target.wants
        * remote-fs-pre.target.requires
        * remote-fs-pre.target.wants
    Most likely, unit files are not generated for "*pre*" targets, but to be
    sure really. Longer list does not cause any issues in this code.

    In most cases, "local-fs.target.requires" is the only important directory
    for us during the upgrade. But in some (sometimes common) cases we will
    need some of the others as well.

    These directories do not have to necessarily exists if there are no mount
    unit files that could be put there. But most likely "local-fs.target.requires"
    will always exists.
    """
    dir_list = [
        'local-fs.target.requires',
        'local-fs.target.wants',
        'local-fs-pre.target.requires',
        'local-fs-pre.target.wants',
        'remote-fs.target.requires',
        'remote-fs.target.wants',
        'remote-fs-pre.target.requires',
        'remote-fs-pre.target.wants',
    ]
    for tdir in dir_list:
        _fix_symlinks_in_dir(dir_containing_mount_units, tdir)


def copy_units_into_system_location(upgrade_container_ctx, dir_with_our_mount_units):
    """
    Copy units and their .wants/.requires directories into the target userspace container.

    :return: A list of files in the target userspace that were created by copying.
    :rtype: list[str]
    """
    dest_inside_container = '/usr/lib/systemd/system'

    api.current_logger().debug(
        'Copying generated mount units for upgrade from {} to {}'.format(
            dir_with_our_mount_units,
            upgrade_container_ctx.full_path(dest_inside_container)
        )
    )

    copied_files = []
    prefix_len_to_drop = len(upgrade_container_ctx.base_dir)

    # We cannot rely on mounting library when copying into container
    # as we want to control what happens to symlinks and
    # shutil.copytree in Python3.6 fails if dst directory exists already
    # - which happens in some cases when copying these files.
    for root, dummy_dirs, files in os.walk(dir_with_our_mount_units):
        rel_path = os.path.relpath(root, dir_with_our_mount_units)
        if rel_path == '.':
            rel_path = ''
        dst_dir = os.path.join(upgrade_container_ctx.full_path(dest_inside_container), rel_path)
        os.makedirs(dst_dir, mode=0o755, exist_ok=True)

        for file in files:
            src_file = os.path.join(root, file)
            dst_file = os.path.join(dst_dir, file)
            api.current_logger().debug(
                'Copying mount unit file {} to {}'.format(src_file, dst_file)
            )
            if os.path.islink(dst_file):
                # If the target file already exists and it is a symlink, it will
                # fail and we want to overwrite this.
                # NOTE(pstodulk): You could think that it cannot happen, but
                # in future possibly it could happen, so let's rather be careful
                # and handle it. If the dst file exists, we want to overwrite it
                # for sure
                _delete_file(dst_file)
            shutil.copy2(src_file, dst_file, follow_symlinks=False)
            copied_files.append(dst_file[prefix_len_to_drop:])

    return copied_files


def remove_units_for_targets_that_are_already_mounted_by_dracut(dir_with_our_mount_units):
    """
    Remove mount units for mount targets that are already mounted by dracut.

    Namely, remove mount units:
        '-.mount'   (mounts /)
        'usr.mount' (mounts /usr)
    """

    # NOTE: remount-fs.service creates dependency cycles that are nondeterministically broken
    # by systemd, causing unpredictable failures. The service is supposed to remount root
    # and /usr, reapplying mount options from /etc/fstab. However, the fstab file present in
    # the initramfs is not the fstab from the source system, and, therefore, it is pointless
    # to require the service. It would make sense after we switched root during normal boot
    # process.
    already_mounted_units = [
        '-.mount',
        'usr.mount',
        'local-fs.target.wants/systemd-remount-fs.service'
    ]

    for unit in already_mounted_units:
        unit_location = os.path.join(dir_with_our_mount_units, unit)

        if not os.path.exists(unit_location):
            api.current_logger().debug('The {} unit does not exists, no need to remove it.'.format(unit))
            continue

        _delete_file(unit_location)


def request_units_inclusion_in_initramfs(files_to_include):
    api.current_logger().debug('Including the following files into initramfs: {}'.format(files_to_include))

    additional_files = [
        '/usr/sbin/swapon'  # If the system has swap, we have also generated a swap unit to activate it
    ]

    tasks = UpgradeInitramfsTasks(include_files=files_to_include + additional_files)
    api.produce(tasks)


def does_system_have_separate_boot_partition():
    storage_info = next(api.consume(StorageInfo), None)
    if not storage_info:
        err_msg = 'Actor did not receive required information about system storage (StorageInfo)'
        raise StopActorExecutionError(err_msg)

    for fstab_entry in storage_info.fstab:
        if fstab_entry.fs_file == '/boot':
            return True

    return False


def inject_bundled_units(workspace):
    """
    Copy static units that are bundled within this actor into the workspace.
    """
    bundled_units_dir = api.get_actor_folder_path('bundled_units')
    for unit in os.listdir(bundled_units_dir):
        if unit == BIND_MOUNT_SYSROOT_BOOT_UNIT:
            has_separate_boot = does_system_have_separate_boot_partition()
            if not has_separate_boot:
                # We perform bind-mounting because of dracut's fips module.
                # When /boot is not a separate partition, we don't need to bind mount it --
                # the fips module itself will create a symlink.
                continue

        unit_path = os.path.join(bundled_units_dir, unit)
        unit_dst = os.path.join(workspace, unit)
        api.current_logger().debug('Copying static unit bundled within leapp {} to {}'.format(unit, unit_dst))
        shutil.copyfile(unit_path, unit_dst)


def setup_storage_initialization():
    livemode_config = next(api.consume(LiveModeConfig), None)
    if livemode_config and livemode_config.is_enabled:
        api.current_logger().debug('Pre-generation of systemd fstab mount units skipped: The LiveMode is enabled.')
        return

    userspace_info = next(api.consume(TargetUserSpaceInfo), None)
    with mounting.NspawnActions(base_dir=userspace_info.path) as upgrade_container_ctx:
        with tempfile.TemporaryDirectory(dir='/var/lib/leapp/', prefix='tmp_systemd_fstab_') as workspace_path:
            run_systemd_fstab_generator(workspace_path)
            remove_units_for_targets_that_are_already_mounted_by_dracut(workspace_path)
            prefix_all_mount_units_with_sysroot(workspace_path)
            inject_bundled_units(workspace_path)
            fix_symlinks_in_targets(workspace_path)
            mount_unit_files = copy_units_into_system_location(upgrade_container_ctx, workspace_path)
            request_units_inclusion_in_initramfs(mount_unit_files)
