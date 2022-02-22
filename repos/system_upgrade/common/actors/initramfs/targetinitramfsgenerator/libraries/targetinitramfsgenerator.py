from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import InitrdIncludes  # deprecated
from leapp.models import InstalledTargetKernelVersion, TargetInitramfsTasks
from leapp.utils.deprecation import suppress_deprecation

DRACUT_DIR = '/usr/lib/dracut/modules.d/'


def copy_dracut_modules(modules):
    """
    Copy every dracut module with specified path into the expected directory.

    original content is overwritten if exists
    """
    # FIXME: use just python functions instead of shell cmds
    for module in modules:
        if not module.module_path:
            continue
        try:
            # context.copytree_to(module.module_path, os.path.join(DRACUT_DIR, os.path.basename(module.module_path)))
            run(['cp', '-f', '-a', module.module_path, DRACUT_DIR])
        except CalledProcessError as e:
            api.current_logger().error('Failed to copy dracut module "{name}" from "{source}" to "{target}"'.format(
                name=module.name, source=module.module_path, target=DRACUT_DIR), exc_info=True)
            # FIXME: really do we want to raise the error and stop execution completely??....
            raise StopActorExecutionError(
                message='Failed to install dracut modules required in the target initramfs. Error: {}'.format(str(e))
            )


@suppress_deprecation(InitrdIncludes)
def _get_files():
    files = {f for i in api.consume(InitrdIncludes) for f in i.files}
    files.update([f for i in api.consume(TargetInitramfsTasks) for f in i.include_files])
    return files


def _get_modules():
    # NOTE(pstodulk): Duplicated tasks are not filtered out, nor checked in the actor.
    # Currently possible conflicting tasks are detected by the checkinitramfstasks
    # actor that inhibits the upgrade if any conflicts are detected. User is
    # supposed to create any such tasks before the reporting phase, so we
    # are able to check it.
    #
    modules = []
    for task in api.consume(TargetInitramfsTasks):
        modules.extend(task.include_dracut_modules)
    return modules


def process():
    files = _get_files()
    modules = _get_modules()

    if not files and not modules:
        api.current_logger().debug(
            'No additional files or modules required to add into the target initramfs.')
        return

    target_kernel = next(api.consume(InstalledTargetKernelVersion), None)
    if not target_kernel:
        raise StopActorExecutionError(
            'Cannot get version of the installed RHEL-8 kernel',
            details={'Problem': 'Did not receive a message with installed RHEL-8 kernel version'
                                ' (InstalledTargetKernelVersion)'})

    copy_dracut_modules(modules)
    try:
        # multiple files|modules need to be quoted, see --install | --add in dracut(8)
        module_names = list({module.name for module in modules})
        cmd = ['dracut', '-f', '--kver', target_kernel.version]
        if files:
            cmd += ['--install', '{}'.format(' '.join(files))]
        if modules:
            cmd += ['--add', '{}'.format(' '.join(module_names))]
        run(cmd)
    except CalledProcessError as e:
        # just hypothetic check, it should not die
        raise StopActorExecutionError('Cannot regenerate dracut image.', details={'details': str(e)})
