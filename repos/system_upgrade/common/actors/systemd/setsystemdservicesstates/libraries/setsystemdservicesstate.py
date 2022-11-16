from leapp.libraries.common import systemd
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import SystemdServicesTasks


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
        try:
            systemd.enable_unit(service)
        except CalledProcessError:
            # TODO(mmatuska) produce post-upgrade report
            pass

    for service in services_to_disable:
        try:
            systemd.disable_unit(service)
        except CalledProcessError:
            # TODO(mmatuska) produce post-upgrade report
            pass
