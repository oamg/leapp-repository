from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import DefaultInitramfsInfo, DefaultSourceBootEntry


def scan_default_initramfs():
    default_boot_entry = next(api.consume(DefaultSourceBootEntry), None)
    if not default_boot_entry:
        raise StopActorExecutionError('Actor did not receive default boot entry info.')

    try:
        initramfs_info = run(['lsinitrd', '-m', default_boot_entry.initramfs_path], split=True)['stdout']

    except CalledProcessError as err:
        details = {'error': str(err)}
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

        dracut_modules.append(module_line.strip())

    api.current_logger().debug('Default boot entry\'s initramfs (%s) has the following dracut modules: %s',
                               default_boot_entry.initramfs_path, dracut_modules)

    default_initramfs_info_msg = DefaultInitramfsInfo(path=default_boot_entry.initramfs_path,
                                                      used_dracut_modules=dracut_modules)
    api.produce(default_initramfs_info_msg)
