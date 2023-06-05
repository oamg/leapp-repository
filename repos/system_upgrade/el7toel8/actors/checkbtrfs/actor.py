from leapp import reporting
from leapp.actors import Actor
from leapp.models import ActiveKernelModulesFacts
from leapp.reporting import create_report, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckBtrfs(Actor):
    """
    Check if Btrfs filesystem is in use. If yes, inhibit the upgrade process.

    Btrfs filesystem was introduced as Technology Preview with initial releases of RHEL 6 and 7. It
    was deprecated on versions 6.6 and 7.4 and will not be present in next major version.
    """

    name = 'check_btrfs'
    consumes = (ActiveKernelModulesFacts,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):

        hint = 'In order to unload the module from the running system, check the accompanied command.'
        command = ['modprobe', '-r', 'btrfs']

        for fact in self.consume(ActiveKernelModulesFacts):
            for active_module in fact.kernel_modules:
                if active_module.filename == 'btrfs':
                    create_report([
                        reporting.Title('Btrfs has been removed from RHEL8'),
                        reporting.Summary(
                            'The Btrfs file system was introduced as Technology Preview with the '
                            'initial release of Red Hat Enterprise Linux 6 and Red Hat Enterprise Linux 7. As of '
                            'versions 6.6 and 7.4 this technology has been deprecated and removed in RHEL8.'
                        ),
                        reporting.ExternalLink(
                            title='Considerations in adopting RHEL 8 - btrfs has been removed.',
                            url='https://red.ht/file-systems-and-storage-removed-btrfs-rhel-8'
                        ),
                        reporting.ExternalLink(
                            title='How do I prevent a kernel module from loading automatically?',
                            url='https://access.redhat.com/solutions/41278'
                        ),
                        reporting.Severity(reporting.Severity.HIGH),
                        reporting.Groups([reporting.Groups.INHIBITOR]),
                        reporting.Groups([reporting.Groups.FILESYSTEM]),
                        reporting.Remediation(hint=hint, commands=[command]),
                        reporting.RelatedResource('kernel-driver', 'btrfs')
                    ])
                    break
