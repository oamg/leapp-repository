import os
from tempfile import NamedTemporaryFile
from subprocess import check_call
import shutil

from leapp.actors import Actor
from leapp.models import FilteredRpmTransactionTasks, UsedTargetRepositories
from leapp.tags import RPMUpgradePhaseTag, IPUWorkflowTag


class DnfShellRpmUpgrade(Actor):
    name = 'dnf_shell_rpm_upgrade'
    description = 'No description has been provided for the dnf_shell_rpm_upgrade actor.'
    consumes = (FilteredRpmTransactionTasks, UsedTargetRepositories)
    produces = ()
    tags = (RPMUpgradePhaseTag, IPUWorkflowTag)

    def process(self):
        # FIXME: we hitting issue now because the network is down and rhsm
        # # is trying to connect to the server. Commenting this out for now
        # # so people will not be affected in case they do not have set a
        # # release and we will have time to fix it properly.
        # Make sure Subscription Manager OS Release is unset
        #cmd = ['subscription-manager', 'release', '--unset']
        #check_call(cmd)

        dnf_command = [
            '/usr/bin/dnf',
            'shell',
            '-y',
            '--setopt=protected_packages=',
            '--disablerepo', '\'*\'',
            '--releasever', '8',
            '--allowerasing',
            '--best',
            '--nogpgcheck',
            '-C'
        ]

        target_uids = []
        for target_repos in self.consume(UsedTargetRepositories):
            for repo in target_repos.repos:
                target_uids.append(repo.uid)
        dnf_command += ['--enablerepo', ','.join(target_uids)]

        if os.environ.get('LEAPP_DEBUG', '0') == '1':
            dnf_command.append('--debugsolver')

        shutil.copyfile(
            '/etc/yum.repos.d/redhat.repo.upgrade',
            '/etc/yum.repos.d/redhat.repo'
        )

        # FIXME: that's ugly hack, we should get info which file remove and
        # + do it more nicely..
        cmd = ['rm', '-f', '/etc/pki/product/69.pem']
        check_call(cmd)

        data = next(self.consume(FilteredRpmTransactionTasks), FilteredRpmTransactionTasks())
        with NamedTemporaryFile() as script:
            cmds = ['distro-sync']
            cmds += ['remove ' + pkg for pkg in data.to_remove if pkg]
            cmds += ['install ' + pkg for pkg in data.to_install if pkg]

            script.write('\n'.join(cmds))
            script.flush()
            check_call(dnf_command + [script.name])
