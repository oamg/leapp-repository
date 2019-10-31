import os
import shutil

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import dnfplugin, mounting
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api
from leapp.models import (BootContent, RequiredUpgradeInitramPackages, TargetUserSpaceInfo, UpgradeDracutModule,
                          UsedTargetRepositories)

INITRAM_GEN_SCRIPT_NAME = 'generate-initram.sh'


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
        shutil.rmtree(context.full_path('/dracut'))
    except EnvironmentError:
        pass
    for module in modules:
        try:
            context.copytree_to(module.module_path, os.path.join('/dracut', os.path.basename(module.module_path)))
        except shutil.Error as e:
            api.current_logger().error('Failed to copy dracut module "{name}" from "{source}" to "{target}"'.format(
                name=module.name, source=module.module_path, target=context.full_path('/dracut')), exc_info=True)
            raise StopActorExecutionError(
                message='Failed to install dracut modules required in the initram. Error: {}'.format(str(e))
            )


def _get_dracut_modules():
    return list(api.consume(UpgradeDracutModule))


def install_initram_deps(context):
    used_repos = api.consume(UsedTargetRepositories)
    target_userspace_info = next(api.consume(TargetUserSpaceInfo), None)

    packages = set()
    for message in api.consume(RequiredUpgradeInitramPackages):
        packages.update(message.packages)
    dnfplugin.install_initramdisk_requirements(
        packages=packages, target_userspace_info=target_userspace_info, used_repos=used_repos)


def _install_files(context):
    """
    Copy the required files into the `context` userspace and return the list
    of those files.

    Those files will be copied from the source to the userspace used for
    generating of the upgrade initrd. These files may need to be installed
    in the initrd explicitly, so return the list of those files for other
    purposes.
    """
    # TODO: currently we need this just for /etc/dasd.conf, but it's expected
    # we will need this for more files in future. The concept used here will
    # need to be changed, as we should consume specific messages instead.
    # But for now this should be enough. Keeping that for future.
    if architecture.matches_architecture(architecture.ARCH_S390X):
        # we don't need to check existence of the file - it is required on this
        # this architecture
        context.copy_to('/etc/dasd.conf', '/etc/dasd.conf')
        return ['/etc/dasd.conf']
    return []


def install_multipath_files(context):
    # Include multipath related files (according to module-setup of multipath)
    if os.path.exists('/etc/xdrdevices.conf'):
        context.copy_to('/etc/xdrdevices.conf', '/etc/xdrdevices.conf')
    if os.path.exists('/etc/multipath.conf'):
        context.copy_to('/etc/multipath.conf', '/etc/multipath.conf')
        if os.path.isdir('/etc/multipath'):
            shutil.rmtree(context.full_path('/etc/multipath'))
            context.copytree_to('/etc/multipath', '/etc/multipath')


def generate_initram_disk(context):
    """
    Function to actually execute the initram creation.
    """
    generator_script = api.get_actor_file_path(INITRAM_GEN_SCRIPT_NAME)
    if not generator_script:
        raise StopActorExecutionError(
            message='Mandatory script to generate initram not available.',
            details=_reinstall_leapp_repository_hint()
        )
    modules = _get_dracut_modules()
    copy_dracut_modules(context, modules)
    context.copy_to(generator_script, os.path.join('/', INITRAM_GEN_SCRIPT_NAME))
    install_initram_deps(context)
    install_multipath_files(context)
    install_files = _install_files(context)
    # FIXME: issue #376
    context.call([
        '/bin/sh', '-c',
        'LEAPP_ADD_DRACUT_MODULES="{modules}" LEAPP_KERNEL_ARCH={arch} '
        'LEAPP_DRACUT_INSTALL_FILES="{files}" {cmd}'.format(
            modules=','.join([mod.name for mod in modules]),
            arch=api.current_actor().configuration.architecture,
            files=' '.join(install_files),
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
        generate_initram_disk(context)
