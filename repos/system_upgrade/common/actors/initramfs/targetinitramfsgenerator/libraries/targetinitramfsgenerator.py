import errno
import os
import shutil

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import InitrdIncludes  # deprecated
from leapp.models import InstalledTargetKernelInfo, TargetInitramfsTasks
from leapp.utils.deprecation import suppress_deprecation

DRACUT_DIR = '/usr/lib/dracut/modules.d/'


def _get_target_kernel_modules_dir(kernel_version):
    """
    Return the path where the custom kernel modules should be copied.
    """

    modules_dir = os.path.join('/', 'lib', 'modules', kernel_version, 'extra', 'leapp')

    return modules_dir


def _copy_modules(modules, dst_dir, kind):
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
        os.makedirs(dst_dir)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(dst_dir):
            pass
        else:
            raise

    for module in modules:
        if not module.module_path:
            continue

        dst_path = os.path.join(dst_dir, os.path.basename(module.module_path))
        if os.path.exists(dst_path):
            api.current_logger().debug(
                'The {name} {kind} module has been already installed. Skipping.'
                .format(name=module.name, kind=kind))
            continue

        copy_fn = shutil.copytree
        if os.path.isfile(module.module_path):
            copy_fn = shutil.copy2

        try:
            api.current_logger().debug(
                'Copying {kind} module "{name}" to "{path}".'
                .format(kind=kind, name=module.name, path=dst_path))

            copy_fn(module.module_path, dst_path)
        except shutil.Error as e:
            api.current_logger().error(
                    'Failed to copy {kind} module "{name}" from "{source}" to "{target}"'.format(
                        kind=kind, name=module.name, source=module.module_path, target=dst_dir),
                    exc_info=True)
            raise StopActorExecutionError(
                message='Failed to install {kind} modules required in the initram. Error: {error}'.format(
                    kind=kind, error=str(e))
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
    modules = {'dracut': [], 'kernel': []}
    for task in api.consume(TargetInitramfsTasks):
        modules['dracut'].extend(task.include_dracut_modules)
        modules['kernel'].extend(task.include_kernel_modules)

    return modules


def process():
    files = _get_files()
    modules = _get_modules()

    if not files and not modules['kernel'] and not modules['dracut']:
        api.current_logger().debug(
            'No additional files or modules required to add into the target initramfs.')
        return

    target_kernel_info = next(api.consume(InstalledTargetKernelInfo), None)
    if not target_kernel_info:
        raise StopActorExecutionError(
            'Cannot get version of the installed RHEL-8 kernel',
            details={'Problem': 'Did not receive a message with installed RHEL-8 kernel version'
                                ' (InstalledTargetKernelVersion)'})

    _copy_modules(modules['dracut'], DRACUT_DIR, 'dracut')
    _copy_modules(modules['kernel'], _get_target_kernel_modules_dir(target_kernel_info.uname_r), 'kernel')

    # Discover any new modules and regenerate modules.dep
    should_regenerate = any(module.module_path is not None for module in modules['kernel'])
    if should_regenerate:
        try:
            run(['depmod', target_kernel_info.uname_r, '-a'])
        except CalledProcessError as e:
            raise StopActorExecutionError('Failed to generate modules.dep and map files.', details={'details': str(e)})

    try:
        # multiple files|modules need to be quoted, see --install | --add in dracut(8)
        dracut_module_names = list({module.name for module in modules['dracut']})
        kernel_module_names = list({module.name for module in modules['kernel']})
        cmd = ['dracut', '-f', '--kver', target_kernel_info.uname_r]
        if files:
            cmd += ['--install', '{}'.format(' '.join(files))]
        if modules['dracut']:
            cmd += ['--add', '{}'.format(' '.join(dracut_module_names))]
        if modules['kernel']:
            cmd += ['--add-drivers', '{}'.format(' '.join(kernel_module_names))]

        run(cmd)
    except CalledProcessError as e:
        # just hypothetic check, it should not die
        raise StopActorExecutionError('Cannot regenerate dracut image.', details={'details': str(e)})
