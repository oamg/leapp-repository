from leapp.actors import Actor
from leapp.libraries.actor import multipathconfupdate
from leapp.models import MultipathConfFacts
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class MultipathConfUpdate(Actor):
    """
    Modifies multipath configuration files on the target RHEL-8 system so that
    they will run properly. This is done in three ways
    1. commenting out lines for options that no longer exist, or whose value
       is no longer current in RHEL-8
    2. Migrating any options in an devices section with all_devs to an
       overrides sections
    3. Rename options that have changed names
    """

    name = 'multipath_conf_update'
    consumes = (MultipathConfFacts,)
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        facts = next(self.consume(MultipathConfFacts), None)
        if facts is None:
            self.log.debug('Skipping execution. No MultipathConfFacts has '
                           'been produced')
            return
        multipathconfupdate.update_configs(facts)
