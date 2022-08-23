from leapp.actors import Actor
from leapp.libraries.actor import multipathconfread
from leapp.models import InstalledRedHatSignedRPM, MultipathConfFacts8to9, TargetUserSpaceUpgradeTasks
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class MultipathConfRead8to9(Actor):
    """
    Read multipath configuration files and extract the necessary information

    Related files:
      - /etc/multipath.conf
      - /etc/multipath/ - any files inside the directory
      - /etc/xdrdevices.conf

    As well, create task (msg) to copy all needed multipath files into
    the target container as the files are needed to create proper initramfs.
    This covers the files mentioned above.
    """

    name = 'multipath_conf_read_8to9'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (MultipathConfFacts8to9, TargetUserSpaceUpgradeTasks)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self):
        if multipathconfread.is_processable():
            res = multipathconfread.get_multipath_conf_facts()
            if res:
                self.produce(res)
                # Create task to copy multipath config files Iff facts
                # are generated
                multipathconfread.produce_copy_to_target_task()
