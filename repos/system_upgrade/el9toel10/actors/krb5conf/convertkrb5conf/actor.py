from leapp.actors import Actor
from leapp.libraries.actor import convertkrb5conf
from leapp.models import OutdatedKrb5conf
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class ConvertKrb5conf(Actor):
    """
    Update krb5 configuration file
    """

    name = 'convert_krb5_conf'
    consumes = (OutdatedKrb5conf,)
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        convertkrb5conf.process()
