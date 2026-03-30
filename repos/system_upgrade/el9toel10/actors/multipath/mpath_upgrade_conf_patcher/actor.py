from leapp.actors import Actor
from leapp.libraries.actor import mpathconfupdate
from leapp.models import MultipathConfFacts9to10, MultipathConfigUpdatesInfo
from leapp.tags import IPUWorkflowTag, TargetTransactionChecksPhaseTag


class MultipathUpgradeConfUpdate9to10(Actor):
    """
    Modifies multipath configuration files for the RHEL-10 upgrade.

    Removes deprecated options (config_dir, bindings_file, wwids_file,
    prkeys_file) from multipath configuration files. If config_dir is
    set to a non-default directory, ensures all secondary configs are
    moved to /etc/multipath/conf.d/. Creates entries to relocate
    bindings, wwids, and prkeys files to their default RHEL-10
    locations if necessary.
    """

    name = 'multipath_upgrade_conf_update_9to10'
    consumes = (MultipathConfFacts9to10,)
    produces = (MultipathConfigUpdatesInfo,)
    tags = (TargetTransactionChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        facts = next(self.consume(MultipathConfFacts9to10), None)
        if facts is None:
            self.log.debug('Skipping execution. No MultipathConfFacts9to10 has been produced')
            return
        mpathconfupdate.update_configs(facts)
