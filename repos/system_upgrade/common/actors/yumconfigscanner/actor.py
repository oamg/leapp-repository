from leapp.actors import Actor
from leapp.libraries.actor.yumconfigscanner import scan_yum_config
from leapp.models import YumConfig
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class YumConfigScanner(Actor):
    """
    Scans the configuration of the YUM package manager.
    """

    name = 'yum_config_scanner'
    consumes = ()
    produces = (YumConfig,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        scan_yum_config()
