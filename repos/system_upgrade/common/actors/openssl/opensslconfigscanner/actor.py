from leapp.actors import Actor
from leapp.libraries.actor import readconf
from leapp.models import OpenSslConfig
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class OpenSslConfigScanner(Actor):
    """
    Read an OpenSSL configuration file for further analysis.
    """

    name = 'open_ssl_config_scanner'
    consumes = ()
    produces = (OpenSslConfig,)
    tags = (FactsPhaseTag, IPUWorkflowTag,)

    def process(self):
        readconf.scan_config(self.produce)
