import os
import shutil
import tempfile

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import mounting
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import TargetUserSpaceInfo, UpgradeInitramfsTasks


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


def _fix_local_fs_requires(dir_containing_mount_units):
    """
    Fix broken symlinks in local-fs.target.requires due to us modifying (renaming) the mount units.

    The directory local-fs.target.requires contains symlinks to the (mount) units that are required
    in order for the local-fs.target to be reached. However, we renamed these units to reflect
    that we have changed their mount destinations by prefixing the mount destination with /sysroot.
    Hence, we regenerate the symlinks.
    """

    api.current_logger().debug(
        'Removing the old local-fs.target.requires directory from {}.'.format(dir_containing_mount_units)
    )

    localfs_requires_dir = os.path.join(dir_containing_mount_units, 'local-fs.target.requires')

    shutil.rmtree(localfs_requires_dir)
    os.mkdir(localfs_requires_dir)

    api.current_logger().debug('Populating local-fs.target.requires with new symlinks.')

    for unit_file in os.listdir(dir_containing_mount_units):
        if not unit_file.endswith('.mount'):
            continue

        place_fastlink_at = os.path.join(localfs_requires_dir, unit_file)
        fastlink_points_to = os.path.join('../', unit_file)
        try:
            run(['ln', '-s', fastlink_points_to, place_fastlink_at])

            api.current_logger().debug(
                'Dependency on {} created.'.format(unit_file)
            )
        except CalledProcessError as err:
            err_descr = 'Failed to required unit dependencies for local-fs.target in upgrade initramfs.'
            details = {'details': str(err)}
            raise StopActorExecutionError(err_descr, details=details)


def _collect_copied_files(root, prefix_path_to_strip):
    collected_files = []

    for current_root, _, files in os.walk(root):
        for file_name in files:
            file_path = os.path.join(current_root, file_name)
            file_path = file_path[len(prefix_path_to_strip):]
            collected_files.append(file_path)

    return collected_files


def copy_units_into_system_location(upgrade_container_ctx, dir_with_our_mount_units):
    """
    Copy units and their .wants/.requires directories into the target userspace container.

    :return: A list of files in the target userspace that were created by copying.
    :rtype: list[str]
    """
    dest_inside_container = '/usr/lib/systemd/system'

    api.current_logger().debug(
        'Copying our mount units from {} to container\'s {}'.format(
            dir_with_our_mount_units,
            dest_inside_container
        )
    )

    copied_files = []

    # We cannot rely on mounting library when copying into container
    # as we want to control what happens to symlinks
    for _src_path in os.listdir(dir_with_our_mount_units):
        src_path = os.path.join(dir_with_our_mount_units, _src_path)
        dst_path = upgrade_container_ctx.full_path(os.path.join(dest_inside_container, _src_path))

        if os.path.isdir(src_path):
            shutil.copytree(src_path, dst_path, symlinks=True)
            copied_files += _collect_copied_files(dst_path, upgrade_container_ctx.base_dir)
        else:
            shutil.copy2(src_path, dst_path)

            dst_relative_to_container_root = dst_path[len(upgrade_container_ctx.base_dir):]
            copied_files.append(dst_relative_to_container_root)
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


def setup_storage_initialization():
    userspace_info = next(api.consume(TargetUserSpaceInfo), None)

    with mounting.NspawnActions(base_dir=userspace_info.path) as upgrade_container_ctx:
        with tempfile.TemporaryDirectory() as workspace_path:
            run_systemd_fstab_generator(workspace_path)
            remove_units_for_targets_that_are_already_mounted_by_dracut(workspace_path)
            prefix_all_mount_units_with_sysroot(workspace_path)
            _fix_local_fs_requires(workspace_path)
            mount_unit_files = copy_units_into_system_location(upgrade_container_ctx, workspace_path)
            request_units_inclusion_in_initramfs(mount_unit_files)
