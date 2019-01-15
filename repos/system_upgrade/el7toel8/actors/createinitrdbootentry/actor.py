import os

from leapp.actors import Actor
from leapp.tags import IPUWorkflowTag, InterimPreparationPhaseTag
from subprocess import check_call


class CreateInitRdBootEntry(Actor):
    name = 'create_init_rd_boot_entry'
    description = 'No description has been provided for the create_init_rd_boot_entry actor.'
    consumes = ()
    produces = ()
    tags = (IPUWorkflowTag, InterimPreparationPhaseTag)

    def process(self):
        vmlinuz_fpath = self.get_file_path('vmlinuz-upgrade.x86_64')
        initram_fpath = self.get_file_path('initramfs-upgrade.x86_64.img')
        debug = 'debug' if os.getenv('LEAPP_DEBUG', '0') == '1' else ''

        if vmlinuz_fpath is None or initram_fpath is None:
            self.report_error('Could not find vmlinuz-upgrade.x86_64 and/or initramfs-upgrade.x86_64.img '
                              'in the following paths: {}'.format(' '.join(self.files_paths)),
                              details={'solution': 'You may want to try to reinstall "leapp-repository" package'})
            return

        check_call(['/bin/cp', vmlinuz_fpath, initram_fpath, '/boot'])
        check_call([
            '/usr/sbin/grubby',
            '--add-kernel=/boot/vmlinuz-upgrade.x86_64',
            '--initrd=/boot/initramfs-upgrade.x86_64.img',
            '--title=RHEL Upgrade RAMDISK',
            '--copy-default',
            '--make-default',
            '--args="{DEBUG} enforcing=0 rd.plymouth=0 plymouth.enable=0"'.format(DEBUG=debug)
        ])
