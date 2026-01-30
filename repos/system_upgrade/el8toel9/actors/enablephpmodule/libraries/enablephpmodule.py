from leapp.libraries.stdlib import api
from leapp.models import EnabledModules, Module, RpmTransactionTasks

PHP_MODULE_NAME = 'php'
PHP_MODULE_STREAM = '8.2'


def _is_php82_enabled():
    """
    Check if php:8.2 module was enabled on the source system.

    :returns: True if php:8.2 was enabled, False otherwise.
    """
    enabled_modules_msgs = list(api.consume(EnabledModules))

    if not enabled_modules_msgs:
        api.current_logger().warning(
            'Did not receive EnabledModules message. '
            'Cannot determine if php:8.2 module was enabled on the source system.'
        )
        return False

    for msg in enabled_modules_msgs:
        for module in msg.modules:
            if module.name == PHP_MODULE_NAME and module.stream == PHP_MODULE_STREAM:
                api.current_logger().debug('Found php:8.2 module enabled on source system.')
                return True

    return False


def enable_php_module():
    """
    Enable the php:8.2 module on the target system if it was enabled on the source system.
    """
    if not _is_php82_enabled():
        api.current_logger().debug('php:8.2 module not enabled on the source system, nothing to do.')
        return

    api.current_logger().info('Scheduling php:8.2 module for enabling on the target system.')
    api.produce(RpmTransactionTasks(
        modules_to_enable=[Module(name=PHP_MODULE_NAME, stream=PHP_MODULE_STREAM)]
    ))
