from leapp.actors import Actor
from leapp.libraries.actor import library
from leapp.models import OSReleaseFacts
from leapp.reporting import Report
from leapp.tags import IPUWorkflowTag, FactsPhaseTag


class OSReleaseCollector(Actor):
    """
    Provides data about System OS release.

    After collecting data from /etc/os-release file, a message with relevant data will be produced.
    """

    name = 'os_release_collector'
    consumes = ()
    produces = (Report, OSReleaseFacts,)
    tags = (IPUWorkflowTag, FactsPhaseTag,)

    def process(self):
        self.produce(library.get_os_release_info('/etc/os-release'))
