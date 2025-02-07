from leapp.actors import Actor
from leapp.libraries.actor import convertkrb5conf
from leapp.models import OutdatedKrb5confLocation
from leapp.tags import IPUWorkflowTag, ApplicationsPhaseTag


class ConvertKrb5conf(Actor):
    """
    Update krb5 configuration file
    """

    name = 'convert_krb5_conf'
    consumes = (OutdatedKrb5confLocation,)
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        convertkrb5conf.process()
