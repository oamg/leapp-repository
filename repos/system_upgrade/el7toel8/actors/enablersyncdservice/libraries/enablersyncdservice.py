from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api
from leapp.models import SystemdServicesInfoSource, SystemdServicesTasks

SERVICE_NAME = "rsyncd.service"


def _service_enabled_source(service_info, name):
    service_file = next((s for s in service_info.service_files if s.name == name), None)
    return service_file and service_file.state == "enabled"


def process():
    service_info_source = next(api.consume(SystemdServicesInfoSource), None)
    if not service_info_source:
        raise StopActorExecutionError(
            "Expected SystemdServicesInfoSource message, but didn't get any"
        )

    if _service_enabled_source(service_info_source, SERVICE_NAME):
        api.produce(SystemdServicesTasks(to_enable=[SERVICE_NAME]))
