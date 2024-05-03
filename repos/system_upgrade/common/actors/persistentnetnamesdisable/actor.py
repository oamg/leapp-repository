import re

from leapp import reporting
from leapp.actors import Actor
from leapp.models import KernelCmdlineArg, PersistentNetNamesFacts
from leapp.reporting import create_report, Report
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class PersistentNetNamesDisable(Actor):
    """
    Disable systemd-udevd persistent network naming on machine with single eth0 NIC
    """

    name = 'persistentnetnamesdisable'
    consumes = (PersistentNetNamesFacts,)
    produces = (KernelCmdlineArg, Report)
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
        elif len(interfaces) > 1 and self.ethX_count(interfaces) > 0:
            create_report([
                reporting.Title('Unsupported network configuration'),
                reporting.Summary(
                    'Detected multiple physical network interfaces where one or more use kernel naming (e.g. eth0). '
                    'Upgrade process can not continue because stability of names can not be guaranteed. '
                    'Please read the article at https://access.redhat.com/solutions/4067471 for more information.'
                ),
                reporting.ExternalLink(
                    title='How to perform an in-place upgrade to RHEL 8 when using kernel NIC names on RHEL 7',
                    url='https://access.redhat.com/solutions/4067471'
                ),
                reporting.ExternalLink(
                    title='RHEL 8 to RHEL 9: inplace upgrade fails at '
                          '"Network configuration for unsupported device types detected"',
                    url='https://access.redhat.com/solutions/7009239'
                ),
                reporting.Remediation(
                    hint='Rename all ethX network interfaces following the attached KB solution article.'
                ),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Groups([reporting.Groups.NETWORK]),
                reporting.Groups([reporting.Groups.INHIBITOR])
            ])
