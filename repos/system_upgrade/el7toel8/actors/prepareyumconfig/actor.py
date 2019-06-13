from leapp.actors import Actor
from leapp.libraries.common import utils
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
        utils.apply_yum_workaround()
