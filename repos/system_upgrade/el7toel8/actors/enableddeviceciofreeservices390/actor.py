from leapp.actors import Actor
from leapp.libraries.actor import enabledeviceciofreeservice
from leapp.models import SystemdServicesTasks
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class EnableDeviceCioFreeService(Actor):
    """
    Enables device_cio_free.service systemd service on s390x

    After an upgrade this service ends up disabled even though it's vendor preset is set to enabled.
    The service is used to enable devices which are not explicitly enabled on the kernel command line.
    """

    name = 'enable_device_cio_free_service'
    consumes = ()
    produces = (SystemdServicesTasks,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        enabledeviceciofreeservice.process()
