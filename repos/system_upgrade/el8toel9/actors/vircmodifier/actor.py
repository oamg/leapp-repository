from leapp.actors import Actor
from leapp.libraries.actor import vircmodifier
from leapp.models import VircConfig
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class VircModifier(Actor):
    """
    Remove obsolete lines from /etc/virc during RHEL 8 to 9 upgrade.

    Consumes VircConfig produced by VircScanner and removes the flagged lines.
    """

    name = 'virc_modifier'
    consumes = (VircConfig,)
    produces = ()
    tags = (IPUWorkflowTag, ApplicationsPhaseTag,)

    def process(self):
        vircmodifier.process(self.consume(VircConfig))
