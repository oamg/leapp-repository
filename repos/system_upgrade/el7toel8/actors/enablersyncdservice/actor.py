from leapp.actors import Actor
from leapp.libraries.actor import enablersyncdservice
from leapp.models import SystemdServicesInfoSource, SystemdServicesTasks
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class EnableDeviceCioFreeService(Actor):
    """
    Enables rsyncd.service systemd service if it is enabled on source system

    After an upgrade this service ends up disabled even if it was enabled on
    the source system.
    """

    name = 'enable_rsyncd_service'
    consumes = (SystemdServicesInfoSource,)
    produces = (SystemdServicesTasks,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        enablersyncdservice.process()
