import os
import shutil

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import dnfplugin, mounting
from leapp.libraries.stdlib import api
from leapp.models import (
    BootContent,
    RequiredUpgradeInitramPackages,  # deprecated
    TargetUserSpaceInfo,
    TargetUserSpaceUpgradeTasks,
    UpgradeDracutModule,  # deprecated
    UpgradeInitramfsTasks,
    UsedTargetRepositories,
)
from leapp.utils.deprecation import suppress_deprecation

INITRAM_GEN_SCRIPT_NAME = 'generate-initram.sh'
DRACUT_DIR = '/dracut'


def _reinstall_leapp_repository_hint():
    """
    Convenience function for creating a detail for StopActorExecutionError with a hint to reinstall the
    leapp-repository package
    """
    return {
        'hint': 'Try to reinstall the `leapp-repository` package.'
    }


def copy_dracut_modules(context, modules):
    """
    Copies our dracut modules into the target userspace.
    """
    try:
        shutil.rmtree(context.full_path(DRACUT_DIR))
    except EnvironmentError:
        pass
    for module in modules:
        if not module.module_path:
            continue
        try:
            context.copytree_to(module.module_path, os.path.join(DRACUT_DIR, os.path.basename(module.module_path)))
        except shutil.Error as e:
            api.current_logger().error('Failed to copy dracut module "{name}" from "{source}" to "{target}"'.format(
                name=module.name, source=module.module_path, target=context.full_path(DRACUT_DIR)), exc_info=True)
            raise StopActorExecutionError(
                message='Failed to install dracut modules required in the initram. Error: {}'.format(str(e))
            )


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


# duplicate of _copy_files fro userspacegen.py
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


# TODO: think about possibility to split this part to different actor
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


def generate_initram_disk(context):
    """
    Function to actually execute the init ramdisk creation.

    Includes handling of specified dracut modules from the host when needed
    """
    # TODO: (maybe for Cabal)
    # It could be nice to be sure we have every module specified just
    # once and in case a same module name is specified multiple times:
    # a) log debug/info msg when module is specified multiple times, but
    # # it is identitical (same paths, ...)
    # b) raise error, when module is specified multiple times and paths are
    # #  different (add possibility to skip the check when an envar is used)
    modules = _get_dracut_modules()  # deprecated
    files = set()
    for task in api.consume(UpgradeInitramfsTasks):
        modules.extend(task.include_dracut_modules)
        files.update(task.include_files)
    copy_dracut_modules(context, modules)
    # FIXME: issue #376
    context.call([
        '/bin/sh', '-c',
        'LEAPP_ADD_DRACUT_MODULES="{modules}" LEAPP_KERNEL_ARCH={arch} '
        'LEAPP_DRACUT_INSTALL_FILES="{files}" {cmd}'.format(
            modules=','.join([mod.name for mod in modules]),
            arch=api.current_actor().configuration.architecture,
            files=' '.join(files),
            cmd=os.path.join('/', INITRAM_GEN_SCRIPT_NAME))
    ])
    copy_boot_files(context)


def copy_boot_files(context):
    """
    Function to copy the generated initram and corresponding kernel to /boot - Additionally produces a BootContent
    message with their location.
    """
    curr_arch = api.current_actor().configuration.architecture
    kernel = 'vmlinuz-upgrade.{}'.format(curr_arch)
    initram = 'initramfs-upgrade.{}.img'.format(curr_arch)
    content = BootContent(
        kernel_path=os.path.join('/boot', kernel),
        initram_path=os.path.join('/boot', initram)
    )

    context.copy_from(os.path.join('/artifacts', kernel), content.kernel_path)
    context.copy_from(os.path.join('/artifacts', initram), content.initram_path)

    api.produce(content)


def process():
    userspace_info = next(api.consume(TargetUserSpaceInfo), None)

    with mounting.NspawnActions(base_dir=userspace_info.path) as context:
        prepare_userspace_for_initram(context)
        generate_initram_disk(context)
