import os

from leapp.actors import Actor
from leapp.libraries.actor import library
from leapp.libraries.common.utils import read_file
from leapp.models import InstalledRedHatSignedRPM, SpamassassinFacts
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class SpamassassinConfigRead(Actor):
    """
    Reads spamc configuration (/etc/mail/spamassassin/spamc.conf), the
    spamassassin sysconfig file (/etc/sysconfig/spamassassin) and checks
    whether the spamassassin service has been overriden. Produces
    SpamassassinFacts containing the extracted information.
    """

    name = 'spamassassin_config_read'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (SpamassassinFacts,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        if library.is_processable():
            self.produce(library.get_spamassassin_facts(read_func=read_file,
                                                        listdir=os.listdir))
