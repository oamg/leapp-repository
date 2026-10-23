from leapp.actors import Actor
from leapp.libraries.actor import removeresumeservice
from leapp.reporting import Report
from leapp.tags import FirstBootPhaseTag, IPUWorkflowTag


class RemoveSystemdResumeService(Actor):
    """
    Remove systemd service to launch Leapp.

    After system was rebooted and process resumed, this service is not necessary anymore.
    """

    name = 'remove_systemd_resume_service'
    consumes = ()
    produces = (Report,)
    tags = (FirstBootPhaseTag.After, IPUWorkflowTag)

    def process(self):
        removeresumeservice.process()
