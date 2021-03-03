from leapp.actors import Actor
from leapp.exceptions import StopActorExecutionError
from leapp.models import FstabContents
from leapp.tags import IPUWorkflowTag, FactsPhaseTag


class GetFstabContents(Actor):
    """
    Read the contents of /etc/fstab for later processing.
    """

    name = 'get_fstab_contents'
    consumes = ()
    produces = (FstabContents,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        try:
            with open('/etc/fstab') as f:
                self.produce(FstabContents(lines=f.readlines()))
        except (IOError, OSError):
            raise StopActorExecutionError(message='Could not open /etc/fstab for reading')
