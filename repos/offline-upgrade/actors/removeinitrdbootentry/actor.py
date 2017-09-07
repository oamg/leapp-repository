from leapp.actors import Actor
from leapp.tags import IPUWorkflowTag, InitRamStartPhaseTag
from subprocess import check_call


class RemoveInitRdBootEntry(Actor):
    name = 'remove_init_rd_boot_entry'
    description = 'No description has been provided for the remove_init_rd_boot_entry actor.'
    consumes = ()
    produces = ()
    tags = (IPUWorkflowTag, InitRamStartPhaseTag)

    def process(self):
        check_call([
            '/bin/mount', '-a'
        ])
        check_call([
            '/usr/sbin/grubby',
            '--remove-kernel=/boot/vmlinuz-upgrade.x86_64'
        ])
