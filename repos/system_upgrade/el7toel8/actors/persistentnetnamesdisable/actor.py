import re

from leapp.libraries.common import reporting

from leapp.actors import Actor
from leapp.models import PersistentNetNamesFacts, KernelCmdlineArg
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class PersistentNetNamesDisable(Actor):
    """
    Disable systemd-udevd persistent network naming on machine with single eth0 NIC
    """

    name = 'persistentnetnamesdisable'
    consumes = (PersistentNetNamesFacts,)
    produces = (KernelCmdlineArg,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def ethX_count(self, interfaces):
        ethX = re.compile('eth[0-9]+')
        count = 0

        for i in interfaces:
            if ethX.match(i.name):
                count = count + 1
        return count

    def single_eth0(self, interfaces):
        return len(interfaces) == 1 and interfaces[0].name == 'eth0'

    def disable_persistent_naming(self):
        self.log.info("Single eth0 network interface detected. Appending 'net.ifnames=0' to RHEL-8 kernel commandline")
        self.produce(KernelCmdlineArg(**{'key': 'net.ifnames', 'value': '0'}))

    def process(self):
        interfaces = next(self.consume(PersistentNetNamesFacts)).interfaces

        if self.single_eth0(interfaces):
            self.disable_persistent_naming()
        elif self.ethX_count(interfaces) > 1:
            reporting.report_generic(
                title='Unsupported network configuration',
                summary='Detected multiple network interfaces using unstable kernel names (e.g. eth0, eth1). '
                        'Upgrade process can not continue because stability of names can not be guaranteed. '
                        'Please read the article at https://access.redhat.com/solutions/4067471 for more information.',
                severity='high',
                flags=['inhibitor'])
