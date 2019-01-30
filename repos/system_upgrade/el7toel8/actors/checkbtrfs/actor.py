from leapp.actors import Actor
from leapp.models import Inhibitor, ActiveKernelModulesFacts
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckBtrfs(Actor):
    name = 'check_btrfs'
    description = 'Check if Btrfs filesystem is in use. If yes, inhibit the upgrade process'
    consumes = (ActiveKernelModulesFacts,)
    produces = (Inhibitor,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        for fact in self.consume(ActiveKernelModulesFacts):
            for active_module in fact.kernel_modules:
                if active_module.filename == 'btrfs':
                    self.produce(Inhibitor(
                        summary='Btrfs removed on next major version',
                        details='The Btrfs file system was introduced as Technology Preview with the initial release '
                                'of Red Hat Enterprise Linux 6 and Red Hat Enterprise Linux 7. As of versions 6.6 and '
                                '7.4 this technology has been deprecated and will be removed in next major version',
                        solutions='Please consider migrating your Btrfs mount point(s) to a different filesystem '
                                  'before next upgrade attempt. If no Btrfs filesystem is in use, please unload '
                                  'btrfs kernel module running "# rmmod btrfs"'))
                    break
