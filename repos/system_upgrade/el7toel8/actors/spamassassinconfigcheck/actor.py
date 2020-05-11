from leapp.actors import Actor
from leapp.libraries.actor import spamassassinconfigcheck
from leapp.models import Report, SpamassassinFacts
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class SpamassassinConfigCheck(Actor):
    """
    Reports changes in spamassassin between RHEL-7 and RHEL-8

    Reports backward-incompatible changes that have been made in spamassassin
    between RHEL-7 and RHEL-8 (spamc no longer accepts an argument with the --ssl
    option; spamd no longer accepts the --ssl-version; SSLv3 is no longer supported;
    the type of spamassassin.service has been changed from "forking" to "simple";
    sa-update no longer supports SHA1 validation of rule files).

    The migration of the configuration files will be mostly handled by the
    SpamassassinConfigUpdate actor, however the admin still needs to know about
    the changes so that they can do any necessary migration in places that we cannot
    reach (e.g. scripts).
    """

    name = 'spamassassin_config_check'
    consumes = (SpamassassinFacts,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        facts = next(self.consume(SpamassassinFacts), None)
        if facts:
            spamassassinconfigcheck.produce_reports(facts)
        else:
            self.log.debug('Skipping execution - no SpamassassinFacts message has been produced.')
