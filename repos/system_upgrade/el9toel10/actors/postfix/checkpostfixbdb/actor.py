from leapp.actors import Actor
from leapp.libraries.actor import checkpostfixbdb
from leapp.models import PostfixBdbConfiguration, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckPostfixBdb(Actor):
    """
    Warn when Postfix still uses Berkeley DB hash/btree maps.

    Those map types are not available on RHEL 10. The administrator must
    convert them to lmdb; Leapp does not rewrite Postfix configuration
    automatically because the layouts can be complex.
    """

    name = 'check_postfix_bdb'
    consumes = (PostfixBdbConfiguration,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        checkpostfixbdb.process()
