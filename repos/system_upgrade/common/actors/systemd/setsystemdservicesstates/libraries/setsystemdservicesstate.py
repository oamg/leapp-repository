from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import SystemdServicesTasks


def _try_set_service_state(command, service):
    try:
        # it is possible to call this on multiple units at once,
        # but failing to enable one service would cause others to not enable as well
        run(['systemctl', command, service])
    except CalledProcessError as err:
        api.current_logger().error('Failed to {} systemd unit "{}". Message: {}'.format(command, service, str(err)))
        # TODO(mmatuska) produce post-upgrade report


def process():
    services_to_enable = set()
    services_to_disable = set()
    for task in api.consume(SystemdServicesTasks):
        services_to_enable.update(task.to_enable)
        services_to_disable.update(task.to_disable)

    intersection = services_to_enable.intersection(services_to_disable)
    for service in intersection:
        msg = 'Attempted to both enable and disable systemd service "{}", service will be disabled.'.format(service)
        api.current_logger().error(msg)

    for service in services_to_enable:
        _try_set_service_state('enable', service)

    for service in services_to_disable:
        _try_set_service_state('disable', service)
