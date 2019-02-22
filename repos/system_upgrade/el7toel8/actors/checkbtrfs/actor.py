from leapp.actors import Actor
from leapp.models import ActiveKernelModulesFacts
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag
from leapp.reporting import Report
from leapp.libraries.common.reporting import report_with_remediation


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
                    report_with_remediation(
                        title='Btrfs removed in the next major version',
                        summary='The Btrfs file system was introduced as Technology Preview with the initial release '
                                'of Red Hat Enterprise Linux 6 and Red Hat Enterprise Linux 7. As of versions 6.6 and '
                                '7.4 this technology has been deprecated and will be removed in next major version.',
                        remediation='Please consider migrating your Btrfs mount point(s) to a different filesystem '
                                    'before next upgrade attempt. If no Btrfs filesystem is in use, please unload '
                                    'btrfs kernel module running "# rmmod btrfs".',
                        severity='high',
                        flags=['inhibitor'])
                    break
