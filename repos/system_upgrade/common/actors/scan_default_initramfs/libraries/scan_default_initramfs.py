from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import DefaultInitramfsInfo, DefaultSourceBootEntry


def scan_default_initramfs():
    default_boot_entry = next(api.consume(DefaultSourceBootEntry), None)
    if not default_boot_entry:
        raise StopActorExecutionError('Actor did not receive default boot entry info.')

    target_initramfs_path = default_boot_entry.initramfs_path
    try:
        initramfs_info = run(['lsinitrd', '-m', target_initramfs_path], split=True)['stdout']

    except CalledProcessError as err:
        details = {'details': str(err)}
        msg = 'Failed to list details (lsinitrd) of the default boot entry\'s initramfs.'
        raise StopActorExecutionError(msg, details=details)

    dracut_modules_lines = iter(initramfs_info)

    for line in dracut_modules_lines:  # Consume everything until `dracut-modules:` is seen
        line = line.strip()
        if line == 'dracut modules:':
            break

    dracut_modules = []
    for module_line in dracut_modules_lines:
        module_line = module_line.strip()
        if module_line.startswith('========'):
            break

        dracut_modules.append(module_line)

    api.current_logger().debug(('Default boot entry\'s initramfs ({}) has '
                                'the following dracut modules: {}').format(default_boot_entry.initramfs_path,
                                                                           dracut_modules))

    default_initramfs_info_msg = DefaultInitramfsInfo(path=default_boot_entry.initramfs_path,
                                                      used_dracut_modules=dracut_modules)
    api.produce(default_initramfs_info_msg)
