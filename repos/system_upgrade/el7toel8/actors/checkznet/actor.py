
from leapp import reporting
from leapp.actors import Actor
from leapp.libraries.actor import library
from leapp.libraries.common.config import architecture
from leapp.reporting import Report
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class CheckZnet(Actor):
    """
    Inhibit upgrade on the s390x architecture when rd.znet is specified on kernel cmdline.

    Some s390x machines have broken networking after the upgrade on RHEL 8.
    Currently we are not able to tell why and which machines have this problem,
    but one of possible workrounds could be remove of the rd.znet parameter
    from the kernel cmdline. But such change can break networking as well, e.g.
    in case a VLAN is set. This is temporary solution, until we discover the
    root of the problem and resolve it.
    """

    name = 'checkznet'
    consumes = ()
    produces = (Report,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        if not architecture.matches_architecture(architecture.ARCH_S390X):
            return

        cmdline = library.get_kernel_cmdline()
        if library.znet_is_set(cmdline):
            _report = [
                reporting.Title('Detected the rd.znet parameter in kernel cmdline'),
                reporting.Severity(reporting.Severity.HIGH),
                reporting.Tags(([reporting.Tags.SANITY])),
                reporting.Flags(([reporting.Flags.INHIBITOR])),
                reporting.Summary(
                    'Upgrade on s390x machines with the rd.znet kernel'
                    ' parameter is not supported and the upgrade has been'
                    ' inhibited.'
                )
            ]

            if not library.vlan_is_used():
                hint = (
                    'If you want to continue, remove the rd.znet parameter from'
                    ' the kernel cmdline using grubby and zipl tools and reboot.'
                    ' But only in case you are sure you do not the parameter'
                    ' specified to have working network. E.g. in case you are'
                    ' using VLAN, you should not do that.'
                )
                _report.append(reporting.Remediation(hint=hint))
            reporting.create_report(_report)
