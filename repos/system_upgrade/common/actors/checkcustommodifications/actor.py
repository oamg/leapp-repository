from leapp.actors import Actor
from leapp.libraries.actor import checkcustommodifications
from leapp.models import CustomModifications, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckCustomModificationsActor(Actor):
    """
    Checks CustomModifications messages and produces a report about files in leapp directories that have been
    modified or newly added.
    """

    name = 'check_custom_modifications_actor'
    consumes = (CustomModifications,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        checkcustommodifications.report_any_modifications()
