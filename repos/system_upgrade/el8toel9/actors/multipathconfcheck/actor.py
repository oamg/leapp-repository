from leapp.actors import Actor
from leapp.libraries.actor import multipathconfcheck
from leapp.models import MultipathConfFacts8to9
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class MultipathConfCheck8to9(Actor):
    """
    Checks if changes to the multipath configuration files are necessary
    for upgrading to RHEL9, and reports the results.
    """

    name = 'multipath_conf_check_8to9'
    consumes = (MultipathConfFacts8to9,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        facts = next(self.consume(MultipathConfFacts8to9), None)
        if facts is None:
            self.log.debug('Skipping execution. No MultipathConfFacts8to9 has '
                           'been produced')
            return
        multipathconfcheck.check_configs(facts)
