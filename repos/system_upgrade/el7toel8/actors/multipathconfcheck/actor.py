from leapp.actors import Actor
from leapp.libraries.actor import multipathconfcheck
from leapp.models import MultipathConfFacts
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class MultipathConfCheck(Actor):
    '''
    Checks whether the multipath configuration can be updated to RHEL-8.
    Specifically, it checks if the path_checker/checker option is set to
    something other than tur in the defaults section. If so, non-trivial
    changes may be required in the multipath.conf file, and it is not
    possible to auto-update it.
    '''

    name = 'multipath_conf_check'
    consumes = (MultipathConfFacts,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        facts = next(self.consume(MultipathConfFacts), None)
        if facts is None:
            self.log.debug('Skipping execution. No MultipathConfFacts has ' +
                           'been produced')
            return
        multipathconfcheck.check_configs(facts)
