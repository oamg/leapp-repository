from leapp.actors import Actor
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import run, CalledProcessError
from leapp.tags import IPUWorkflowTag, PreparationPhaseTag


class Prepareyumconfig(Actor):
    """
    Handle migration of the yum configuration files.

    RPM cannot handle replacement of directories by symlinks by default
    without the %pretrans scriptlet. As yum package is packaged wrong,
    we have to workround that by migration of the yum configuration files
    before the rpm transaction is processed.
    """

    name = 'prepareyumconfig'
    consumes = ()
    produces = ()
    tags = (IPUWorkflowTag, PreparationPhaseTag)

    def process(self):
        try:
            run(['handleyumconfig'])
        except CalledProcessError as e:
            raise StopActorExecutionError(
                    'Migration of yum configuration failed.',
                    details={'details': str(e)})
