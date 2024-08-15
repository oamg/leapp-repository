import itertools
import os
import shutil
from collections import namedtuple

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import dnfplugin, mounting
from leapp.libraries.common.config.version import get_target_major_version
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import RequiredUpgradeInitramPackages  # deprecated
from leapp.models import UpgradeDracutModule  # deprecated
from leapp.models import (
    BootContent,
    LiveModeConfig,
    TargetOSInstallationImage,
    TargetUserSpaceInfo,
    TargetUserSpaceUpgradeTasks,
    UpgradeInitramfsTasks,
    UsedTargetRepositories
)
from leapp.utils.deprecation import suppress_deprecation

INITRAM_GEN_SCRIPT_NAME = 'generate-initram.sh'
DRACUT_DIR = '/dracut'
DEDICATED_LEAPP_PART_URL = 'https://access.redhat.com/solutions/7011704'


def _get_target_kernel_version(context):
    """
    Get the version of the most recent kernel version within the container.
    """

    kernel_version = None
    try:
        # NOTE: Currently we install/use always kernel-core in the upgrade
        # initramfs. We do not use currently any different kernel package
        # in the container. Note this could change in future e.g. on aarch64
        # for IPU 9 -> 10.
        # TODO(pstodulk): Investigate situation on ARM systems. OAMG-11433
        results = context.call(['rpm', '-qa', 'kernel-core'], split=True)['stdout']
    except CalledProcessError:
        raise StopActorExecutionError(
            'Cannot get version of the installed kernel inside container.',
            details={'Problem': 'Could not query the currently installed kernel inside container using rpm.'})

    if len(results) > 1:
        # this is should not happen. It's hypothetic situation, which alone it's
        # already error. So skipping more sophisticated implementation.
        # The container is always created during the upgrade and as that we expect
        # always one-and-only kernel installed.
        raise StopActorExecutionError(
            'Cannot get version of the installed kernel inside container.',
            details={'Problem': 'Detected unexpectedly multiple kernels inside target userspace container.'}
        )

    # kernel version == version-release from package
    kernel_version = '-'.join(results[0].rsplit("-", 2)[-2:])
    api.current_logger().debug('Detected kernel version inside container: {}.'.format(kernel_version))

    if not kernel_version:
        raise StopActorExecutionError(
            'Cannot get version of the installed kernel inside container.',
            details={'Problem': 'An rpm query for the available kernels did not produce any results.'})

    return kernel_version


def _get_target_kernel_modules_dir(context):
    """
    Return the path where the custom kernel modules should be copied.
    """

    kernel_version = _get_target_kernel_version(context)
    modules_dir = os.path.join('/', 'lib', 'modules', kernel_version, 'extra', 'leapp')

    return modules_dir


def _reinstall_leapp_repository_hint():
    """
    Convenience function for creating a detail for StopActorExecutionError with a hint to reinstall the
    leapp-repository package
    """
    return {
        'hint': 'Try to reinstall the `leapp-repository` package.'
    }


def _copy_modules(context, modules, dst_dir, kind):
    """
    Copy modules of given kind to the specified destination directory.

    Attempts to remove an cleanup by removing the existing destination
    directory. If the directory does not exist, it is created anew. Then, for
    each module message, it checks if the module has a module path specified. If
    the module already exists in the destination directory, a debug message is
    logged, and the operation is skipped. Otherwise, the module is copied to the
    destination directory.

    """

    try:
        context.remove_tree(dst_dir)
    except EnvironmentError:
        pass

    context.makedirs(dst_dir)

    for module in modules:
        if not module.module_path:
            continue

        dst_path = os.path.join(dst_dir, os.path.basename(module.module_path))
        if os.path.exists(context.full_path(dst_path)):
            api.current_logger().debug(
                'The {name} {kind} module has been already installed. Skipping.'
                .format(name=module.name, kind=kind))
            continue

        copy_fn = context.copytree_to
        if os.path.isfile(module.module_path):
            copy_fn = context.copy_to

        try:
            api.current_logger().debug(
                'Copying {kind} module "{name}" to "{path}".'
                .format(kind=kind, name=module.name, path=dst_path))

            copy_fn(module.module_path, dst_path)
        except shutil.Error as e:
            api.current_logger().error(
                    'Failed to copy {kind} module "{name}" from "{source}" to "{target}"'.format(
                        kind=kind, name=module.name, source=module.module_path, target=context.full_path(dst_dir)),
                    exc_info=True)
            raise StopActorExecutionError(
                message='Failed to install {kind} modules required in the initram. Error: {error}'.format(
                    kind=kind, error=str(e))
            )


def copy_dracut_modules(context, modules):
    """
    Copy dracut modules into the target userspace.

    If a module cannot be copied, an error message is logged, and a
    StopActorExecutionError exception is raised.
    """

    _copy_modules(context, modules, DRACUT_DIR, 'dracut')


def copy_kernel_modules(context, modules):
    """
    Copy kernel modules into the target userspace.

    If a module cannot be copied, an error message is logged, and a
    StopActorExecutionError exception is raised.
    """

    dst_dir = _get_target_kernel_modules_dir(context)
    _copy_modules(context, modules, dst_dir, 'kernel')


@suppress_deprecation(UpgradeDracutModule)
def _get_dracut_modules():
    return list(api.consume(UpgradeDracutModule))


def _install_initram_deps(packages):
    used_repos = api.consume(UsedTargetRepositories)
    target_userspace_info = next(api.consume(TargetUserSpaceInfo), None)

    dnfplugin.install_initramdisk_requirements(
        packages=packages,
        target_userspace_info=target_userspace_info,
        used_repos=used_repos)


# duplicate of _copy_files from userspacegen.py
def _copy_files(context, files):
    """
    Copy the files/dirs from the host to the `context` userspace

    :param context: An instance of a mounting.IsolatedActions class
    :type context: mounting.IsolatedActions class
    :param files: list of files that should be copied from the host to the context
    :type files: list of CopyFile
    """
    for file_task in files:
        if not file_task.dst:
            file_task.dst = file_task.src
        if os.path.isdir(file_task.src):
            context.remove_tree(file_task.dst)
            context.copytree_to(file_task.src, file_task.dst)
        else:
            context.copy_to(file_task.src, file_task.dst)


# TODO(pstodulk): think about possibility to split this part to different actor
# # reasoning: the environment could be prepared automatically and actor
# # developers will be able to do additional modifications before the initrd
# # will be really generated. E.g. multipath: config files will be copied
# # and another actor can securely updated configuration before the initrd
# # will be generated. same could be from user's POV - they are not allowed to
# # modify our actors, but they could need to do additional actions inside the
# # env as well.
@suppress_deprecation(RequiredUpgradeInitramPackages)
def prepare_userspace_for_initram(context):
    """
    Prepare the target userspace container to be able to generate init ramdisk

    This includes installation of rpms that are not installed yet. Copying
    files from the host to container, ... So when we start the process of
    the upgrade init ramdisk creation, the environment will be prepared with
    all required data and utilities.

    Note: preparation of dracut modules are handled outside of this function
    """
    packages = set()
    files = []
    _cftuples = set()

    def _update_files(copy_files):
        # add just uniq CopyFile objects to omit duplicate copying of files
        for cfile in copy_files:
            cftuple = (cfile.src, cfile.dst)
            if cftuple not in _cftuples:
                _cftuples.add(cftuple)
                files.append(cfile)

    generator_script = api.get_actor_file_path(INITRAM_GEN_SCRIPT_NAME)
    if not generator_script:
        raise StopActorExecutionError(
            message='Mandatory script to generate initram not available.',
            details=_reinstall_leapp_repository_hint()
        )
    context.copy_to(generator_script, os.path.join('/', INITRAM_GEN_SCRIPT_NAME))
    for msg in api.consume(TargetUserSpaceUpgradeTasks):
        packages.update(msg.install_rpms)
        _update_files(msg.copy_files)
    for message in api.consume(RequiredUpgradeInitramPackages):
        packages.update(message.packages)
    # install all required rpms first, so files installed/copied later
    # will not be overwritten during the dnf transaction
    _install_initram_deps(packages)
    _copy_files(context, files)


def _get_fspace(path, convert_to_mibs=False, coefficient=1):
    """
    Return the free disk space on given path.

    The default is in bytes, but if convert_to_mibs is True, return MiBs instead.

    Raises OSError if nothing exists on the given `path`.

    :param path: Path to an existing file or directory
    :type path: str
    :param convert_to_mibs: If True, convert the value to MiBs
    :type convert_to_mibs: bool
    :param coefficient: Coefficient to multiply the free space (e.g. 0.9 to have it 10% lower). Max: 1
    :type coefficient: float
    :rtype: int
    """
    # TODO(pstodulk): discuss the function params
    # NOTE(pstodulk): This func is copied from the overlaygen.py lib
    # probably it would make sense to make it public in the utils.py lib,
    # but for now, let's keep it private
    stat = os.statvfs(path)

    coefficient = min(coefficient, 1)
    fspace_bytes = int(stat.f_frsize * stat.f_bavail * coefficient)
    if convert_to_mibs:
        return int(fspace_bytes / 1024 / 1024)  # noqa: W1619; pylint: disable=old-division
    return fspace_bytes


def _check_free_space(context):
    """
    Raise StopActorExecutionError if there is less than 500MB of free space available.

    If there is not enough free space in the context, the initramfs will not be
    generated successfully and it's hard to discover what was the issue. Also
    the missing space is able to kill the leapp itself - trying to write to the
    leapp.db when the FS hosting /var/lib/leapp is full, kills the framework
    and the actor execution too - so there is no gentle way to handle such
    exceptions when it happens. From this point, let's rather check the available
    space in advance and stop the execution when it happens.

    It is not expected to hit this issue, but I was successful and I know
    it's still possible even with all other changes (just it's much harder
    now to hit it). So adding this seatbelt, that is not 100% bulletproof,
    but I call it good enough.

    Currently protecting last 500MB. In case of problems, we can increase
    the value.
    """
    message = 'There is not enough space on the file system hosting /var/lib/leapp.'
    hint = (
        'Increase the free space on the filesystem hosting'
        ' /var/lib/leapp by 500MB at minimum (suggested 1500MB).\n\n'
        'It is also a good practice to create dedicated partition'
        ' for /var/lib/leapp when more space is needed, which can be'
        ' dropped after the system upgrade is fully completed.'
        ' For more info, see: {}'
        .format(DEDICATED_LEAPP_PART_URL)
    )
    detail = (
        'Remaining free space is lower than 500MB which is not enough to'
        ' be able to generate the upgrade initramfs. '
    )

    if _get_fspace(context.base_dir, convert_to_mibs=True) < 500:
        raise StopActorExecutionError(
            message=message,
            details={'hint': hint, 'detail': detail}
        )


InitramfsIncludes = namedtuple('InitramfsIncludes', ('files', 'dracut_modules', 'kernel_modules'))


def collect_initramfs_includes():
    """
    Collect modules and files requested to be included in initramfs.

    :returns: A summary of requested initramfs includes
    :rtype: InitramfsIncludes
    """
    dracut_modules = _get_dracut_modules()  # Use lists as leapp's models are not hashable
    kernel_modules = list()
    additional_initramfs_files = set()

    for task in api.consume(UpgradeInitramfsTasks):
        dracut_modules.extend(task.include_dracut_modules)
        kernel_modules.extend(task.include_kernel_modules)
        additional_initramfs_files.update(task.include_files)

    return InitramfsIncludes(files=list(additional_initramfs_files),
                             dracut_modules=list(dracut_modules),
                             kernel_modules=list(kernel_modules))


def generate_initram_disk(context):
    """
    Function to actually execute the init ramdisk creation.

    Includes handling of specified dracut and kernel modules from the host when
    needed. The check for the 'conflicting' modules is in a separate actor.
    """
    _check_free_space(context)
    env = {}
    if get_target_major_version() == '9':
        env = {'SYSTEMD_SECCOMP': '0'}

    # TODO(pstodulk): Add possibility to add particular drivers
    # Issue #645
    initramfs_includes = collect_initramfs_includes()

    copy_dracut_modules(context, initramfs_includes.dracut_modules)
    copy_kernel_modules(context, initramfs_includes.kernel_modules)

    def fmt_module_list(module_list):
        return ','.join(mod.name for mod in module_list)

    # FIXME: issue #376
    context.call([
        '/bin/sh', '-c',
        'LEAPP_KERNEL_VERSION={kernel_version} '
        'LEAPP_ADD_DRACUT_MODULES="{dracut_modules}" LEAPP_KERNEL_ARCH={arch} '
        'LEAPP_ADD_KERNEL_MODULES="{kernel_modules}" '
        'LEAPP_DRACUT_INSTALL_FILES="{files}" {cmd}'.format(
            kernel_version=_get_target_kernel_version(context),
            dracut_modules=fmt_module_list(initramfs_includes.dracut_modules),
            kernel_modules=fmt_module_list(initramfs_includes.kernel_modules),
            arch=api.current_actor().configuration.architecture,
            files=' '.join(initramfs_includes.files),
            cmd=os.path.join('/', INITRAM_GEN_SCRIPT_NAME))
    ], env=env)

    boot_files_info = copy_boot_files(context)
    return boot_files_info


def get_boot_artifact_names():
    """
    Get the name of leapp's initramfs and upgrade kernel.

    :returns: A tuple (kernel_name, initramfs_name).
    :rtype: Tuple[str, str]
    """

    arch = api.current_actor().configuration.architecture

    kernel = 'vmlinuz-upgrade.{}'.format(arch)
    initramfs = 'initramfs-upgrade.{}.img'.format(arch)

    return (kernel, initramfs)


def copy_target_kernel_from_userspace_into_boot(context, target_kernel_ver, kernel_artifact_name):
    userspace_kernel_installation_path = '/lib/modules/{}/vmlinuz'.format(target_kernel_ver)
    api.current_logger().info(
        'Copying target kernel ({0}) into host system\'s /boot'.format(userspace_kernel_installation_path)
    )
    host_kernel_dest = os.path.join('/boot', kernel_artifact_name)
    context.copy_from(userspace_kernel_installation_path, host_kernel_dest)


def _generate_livemode_initramfs(context, userspace_initramfs_dest, target_kernel_ver):
    """
    Generate livemode initramfs

    Collects modifications requested by received messages, synthesize and executed corresponding
    dracut command. The created initramfs is placed at USERSPACE_ARTIFACTS_PATH/<initramfs_artifact_name>
    in the userspace.

    :param userspace_initramfs_dest str: The path at which the generated initramfs will be placed.
    :param target_kernel_ver str: Kernel version installed into the userspace that will be used by the live image.
    :returns: None
    """
    env = {}
    if get_target_major_version() == '9':
        env = {'SYSTEMD_SECCOMP': '0'}

    initramfs_includes = collect_initramfs_includes()

    copy_dracut_modules(context, initramfs_includes.dracut_modules)
    copy_kernel_modules(context, initramfs_includes.kernel_modules)

    dracut_modules = ['livenet', 'dmsquash-live'] + [mod.name for mod in initramfs_includes.dracut_modules]

    cmd = ['dracut', '--verbose', '--compress', 'xz',
           '--no-hostonly', '--no-hostonly-default-device',
           '-o', 'plymouth dash resume ifcfg earlykdump',
           '--lvmconf', '--mdadmconf',
           '--kver', target_kernel_ver, '-f', userspace_initramfs_dest]

    # Add dracut modules
    cmd.extend(itertools.chain(*(('--add', module) for module in dracut_modules)))

    # Add kernel modules
    cmd.extend(itertools.chain(*(('--add-drivers', module.name) for module in initramfs_includes.kernel_modules)))

    try:
        context.call(cmd, env=env)
    except CalledProcessError as error:
        api.current_logger().error('Failed to generate (live) upgrade image. Error: %s', error)
        raise StopActorExecutionError(
            'Cannot generate the initramfs for the live mode.',
            details={'Problem': 'the dracut command failed: {}'.format(cmd)})


def prepare_boot_files_for_livemode(context):
    """
    Generate the initramfs for the live mode  using dracut modules: dracut-live dracut-squash.
    Silently replace upgrade boot images.
    """
    api.current_logger().info('Building initramfs for the live upgrade image.')

    # @Todo(mhecko): See whether we need to do permission manipulation from dracut_install_modules.
    # @Todo(mhecko): We need to handle upgrade kernel HMAC if we ever want to boot with FIPS in livemode

    target_kernel_ver = _get_target_kernel_version(context)
    kernel_artifact_name, initramfs_artifact_name = get_boot_artifact_names()

    copy_target_kernel_from_userspace_into_boot(context, target_kernel_ver, kernel_artifact_name)

    USERSPACE_ARTIFACTS_PATH = '/artifacts'
    context.makedirs(USERSPACE_ARTIFACTS_PATH, exists_ok=True)
    userspace_initramfs_dest = os.path.join(USERSPACE_ARTIFACTS_PATH, initramfs_artifact_name)

    _generate_livemode_initramfs(context, userspace_initramfs_dest, target_kernel_ver)

    api.current_logger().debug('Copying artifacts from userspace into host\'s /boot')
    host_initramfs_dest = os.path.join('/boot', initramfs_artifact_name)
    host_kernel_dest = os.path.join('/boot', kernel_artifact_name)
    context.copy_from(userspace_initramfs_dest, host_initramfs_dest)

    return BootContent(kernel_path=host_kernel_dest,
                       initram_path=host_initramfs_dest,
                       kernel_hmac_path='')


def create_upgrade_hmac_from_target_hmac(original_hmac_path, upgrade_hmac_path, upgrade_kernel):
    # Rename the kernel name stored in the HMAC file as the upgrade kernel is named differently and the HMAC file
    # refers to the real target kernel
    with open(original_hmac_path) as original_hmac_file:
        hmac_file_lines = [line for line in original_hmac_file.read().split('\n') if line]
        if len(hmac_file_lines) > 1:
            details = ('Expected the target kernel HMAC file to containing only one HMAC line, '
                       'found {0}'.format(len(hmac_file_lines)))
            raise StopActorExecutionError('Failed to prepare HMAC file for upgrade kernel.',
                                          details={'details': details})

        # Keep only non-empty strings after splitting on space
        hmac, dummy_target_kernel_name = [fragment for fragment in hmac_file_lines[0].split(' ') if fragment]

    with open(upgrade_hmac_path, 'w') as upgrade_kernel_hmac_file:
        upgrade_kernel_hmac_file.write('{hmac}  {kernel}\n'.format(hmac=hmac, kernel=upgrade_kernel))


def copy_boot_files(context):
    """
    Function to copy the generated initram and corresponding kernel to /boot


    :returns: BootContent message containing the information about where the artifacts can be found.
    """
    curr_arch = api.current_actor().configuration.architecture
    kernel = 'vmlinuz-upgrade.{}'.format(curr_arch)
    initram = 'initramfs-upgrade.{}.img'.format(curr_arch)

    kernel_hmac = '.{0}.hmac'.format(kernel)
    kernel_hmac_path = os.path.join('/boot', kernel_hmac)

    content = BootContent(
        kernel_path=os.path.join('/boot', kernel),
        initram_path=os.path.join('/boot', initram),
        kernel_hmac_path=kernel_hmac_path
    )

    context.copy_from(os.path.join('/artifacts', kernel), content.kernel_path)
    context.copy_from(os.path.join('/artifacts', initram), content.initram_path)

    kernel_hmac_path = context.full_path(os.path.join('/artifacts', kernel_hmac))
    create_upgrade_hmac_from_target_hmac(kernel_hmac_path, content.kernel_hmac_path, kernel)

    return content


def process():
    userspace_info = next(api.consume(TargetUserSpaceInfo), None)
    target_iso = next(api.consume(TargetOSInstallationImage), None)
    livemode_config = next(api.consume(LiveModeConfig), None)

    with mounting.NspawnActions(base_dir=userspace_info.path) as context:
        with mounting.mount_upgrade_iso_to_root_dir(userspace_info.path, target_iso):
            prepare_userspace_for_initram(context)
            if livemode_config and livemode_config.is_enabled:
                boot_file_info = prepare_boot_files_for_livemode(context)
            else:
                boot_file_info = generate_initram_disk(context)
            api.produce(boot_file_info)
