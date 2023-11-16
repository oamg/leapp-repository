from leapp.actors import Actor
from leapp.libraries.actor import scancustommodifications
from leapp.models import CustomModifications
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanCustomModificationsActor(Actor):
    """
    Collects information about files in leapp directories that have been modified or newly added.
    """

    name = 'scan_custom_modifications_actor'
    produces = (CustomModifications,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        for msg in scancustommodifications.scan():
            self.produce(msg)
