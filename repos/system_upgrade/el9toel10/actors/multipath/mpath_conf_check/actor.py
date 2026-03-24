from leapp.actors import Actor
from leapp.libraries.actor import mpath_conf_check
from leapp.models import MultipathConfFacts9to10
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class MultipathConfCheck9to10(Actor):
    """
    Checks if changes to the multipath configuration files are necessary
    for upgrading to RHEL10, and reports the results.
    """

    name = 'multipath_conf_check_9to10'
    consumes = (MultipathConfFacts9to10,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        facts = next(self.consume(MultipathConfFacts9to10), None)
        if facts is None:
            self.log.debug('Skipping execution. No MultipathConfFacts9to10 has '
                           'been produced')
            return
        mpath_conf_check.check_configs(facts)
