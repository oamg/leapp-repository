from leapp.actors import Actor
from leapp.libraries.actor import spamassassinconfigupdate
from leapp.models import SpamassassinFacts
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class SpamassassinConfigUpdate(Actor):
    """
    This actor performs several modifications to spamassassin configuration
    so that spamc and the spamassassin systemd service can be run without error
    on the target system:
    1. Remove arguments given to the --ssl option in spamc configuration
       (/etc/mail/spamassassin/spamc.conf).
    2. Remove --ssl-version options from the spamassassin sysconfig file
       (/etc/sysconfig/spamassassin), or replace them with --ssl, if needed.
    3. Remove the -d/--daemonize option from the spamassassin sysconfig file.

    All files are backed up before they are modified.
    """

    name = 'spamassassin_config_update'
    consumes = (SpamassassinFacts,)
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        facts = next(self.consume(SpamassassinFacts), None)
        if facts:
            spamassassinconfigupdate.migrate_configs(facts)
        else:
            self.log.debug('Skipping execution - no SpamassassinFacts message has been produced.')
