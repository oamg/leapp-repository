from leapp.actors import Actor
from leapp.libraries.actor import checkkrb5conf
from leapp.models import OutdatedKrb5conf, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckKrb5conf(Actor):
    """
    Create report with the location of oudated krb5 configuration files
    """

    name = 'check_krb5_conf'
    consumes = (OutdatedKrb5conf,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        checkkrb5conf.process()
