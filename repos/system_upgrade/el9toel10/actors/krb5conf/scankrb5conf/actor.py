from leapp.actors import Actor
from leapp.libraries.actor.scankrb5conf import fetch_outdated_krb5_conf_files
from leapp.models import OutdatedKrb5conf
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanKrb5conf(Actor):
    """
    Scan the krb5 modular configuration folder for additional conf files
    """

    name = 'scan_krb5_conf'
    consumes = ()
    produces = (OutdatedKrb5conf,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        self.produce(fetch_outdated_krb5_conf_files(['/etc/krb5.conf',
                                                     '/etc/krb5.conf.d']))
