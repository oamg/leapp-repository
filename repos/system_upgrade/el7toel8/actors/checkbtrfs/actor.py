from leapp.actors import Actor
from leapp.models import ActiveKernelModulesFacts
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag
from leapp import reporting
from leapp.reporting import Report, create_report


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
                            url='https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/considerations_in_adopting_rhel_8/file-systems-and-storage_considerations-in-adopting-rhel-8#btrfs-has-been-removed_file-systems-and-storage'  # noqa: E501; pylint: disable=line-too-long
                        ),
                        reporting.Severity(reporting.Severity.HIGH),
                        reporting.Groups([reporting.Groups.FILESYSTEM, reporting.Groups.INHIBITOR]),
                        reporting.RelatedResource('kernel-driver', 'btrfs')
                    ])
                    break
