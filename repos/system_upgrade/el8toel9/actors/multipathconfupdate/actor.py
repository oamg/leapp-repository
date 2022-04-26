from leapp.actors import Actor
from leapp.libraries.actor import multipathconfupdate
from leapp.models import MultipathConfFacts8to9
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class MultipathConfUpdate8to9(Actor):
    """
    Modifies multipath configuration files on the target RHEL-9 system so that
    they will run properly. This is done in three ways
    1. Adding the allow_usb_devices and enable_foreign options to
       /etc/multipath.conf if they are not present, to retain RHEL-8 behavior
    2. Converting any "*" regular expression strings to ".*"
    """

    name = 'multipath_conf_update_8to9'
    consumes = (MultipathConfFacts8to9,)
    produces = ()
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)

    def process(self):
        facts = next(self.consume(MultipathConfFacts8to9), None)
        if facts is None:
            self.log.debug('Skipping execution. No MultipathConfFacts8to9 has '
                           'been produced')
            return
        multipathconfupdate.update_configs(facts)
