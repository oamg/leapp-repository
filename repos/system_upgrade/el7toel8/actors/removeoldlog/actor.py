from leapp.actors import Actor
from leapp.libraries.actor.library import remove_log
from leapp.tags import IPUWorkflowTag, InterimPreparationPhaseTag


class RemoveOldLog(Actor):
    """
    Remove old log from previous Leapp run.
     
    This is necessary to ensure that you have only valid and updated logs for debugging.
    """

    name = 'remove_old_log'
    consumes = ()
    produces = ()
    tags = (IPUWorkflowTag, InterimPreparationPhaseTag)

    def process(self):
        remove_log()
