import os
import shutil

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import dnfplugin, mounting
from leapp.libraries.stdlib import api
from leapp.models import BootContent, RequiredUpgradeInitramPackages, TargetUserSpaceInfo, UpgradeDracutModule

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
                message='Failed to install dracut modules required in the initram. Error: {}'.format(e.message)
            )


def _get_dracut_modules():
    return list(api.consume(UpgradeDracutModule))


def install_initram_deps(context):
    packages = set()
    for message in api.consume(RequiredUpgradeInitramPackages):
        packages.update(message.packages)
    dnfplugin.install_initramdisk_requirements(packages)


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
    context.call([
        '/bin/sh', '-c',
        'LEAPP_ADD_DRACUT_MODULES={modules} {cmd}'.format(
            modules=','.join([mod.name for mod in modules]),
            cmd=os.path.join('/', INITRAM_GEN_SCRIPT_NAME))
    ])
    copy_boot_files(context)


def copy_boot_files(context):
    """
    Function to copy the generated initram and corresponding kernel to /boot - Additionally produces a BootContent
    message with their location.
    """
    kernel = 'vmlinuz-upgrade.x86_64'
    initram = 'initramfs-upgrade.x86_64.img'
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
