import json
import os
import shutil
import sys
from tempfile import NamedTemporaryFile

from leapp.actors import Actor
from leapp.libraries.stdlib import run
from leapp.libraries.stdlib.call import STDOUT
from leapp.libraries.stdlib.config import is_debug
from leapp.models import FilteredRpmTransactionTasks, UsedTargetRepositories, TransactionCompleted
from leapp.tags import RPMUpgradePhaseTag, IPUWorkflowTag


def _logging_handler(fd_info, buffer):
    '''Custom log handler to always show DNF stdout to console and stderr only in DEBUG mode'''
    (_unused, fd_type) = fd_info

    if fd_type == STDOUT:
        sys.stdout.write(buffer)
    else:
        if is_debug():
            sys.stderr.write(buffer)


class DnfShellRpmUpgrade(Actor):
    """
    Setup and call DNF upgrade command

    Based on previously calculated RPM transaction data, this actor will setup and call
    rhel-upgrade DNF plugin with necessary parameters
    """

    name = 'dnf_shell_rpm_upgrade'
    consumes = (FilteredRpmTransactionTasks, UsedTargetRepositories)
    produces = (TransactionCompleted,)
    tags = (RPMUpgradePhaseTag, IPUWorkflowTag)

    def process(self):
        # FIXME: we hitting issue now because the network is down and rhsm
        # # is trying to connect to the server. Commenting this out for now
        # # so people will not be affected in case they do not have set a
        # # release and we will have time to fix it properly.
        # Make sure Subscription Manager OS Release is unset
        # cmd = ['subscription-manager', 'release', '--unset']
        # run(cmd)

        shutil.copyfile(
            self.get_file_path('rhel_upgrade.py'), '/lib/python2.7/site-packages/dnf-plugins/rhel_upgrade.py')

        dnf_command = ['/usr/bin/dnf', 'rhel-upgrade', 'upgrade']

        target_repoids = []
        for target_repos in self.consume(UsedTargetRepositories):
            for repo in target_repos.repos:
                target_repoids.append(repo.repoid)

        debugsolver = True if os.environ.get('LEAPP_DEBUG', '0') == '1' else False

        shutil.copyfile(
            '/etc/yum.repos.d/redhat.repo.upgrade',
            '/etc/yum.repos.d/redhat.repo'
        )

        # FIXME: that's ugly hack, we should get info which file remove and
        # + do it more nicely..
        cmd = ['rm', '-f', '/etc/pki/product/69.pem']
        run(cmd)

        data = next(self.consume(FilteredRpmTransactionTasks), FilteredRpmTransactionTasks())

        plugin_data = {
            'pkgs_info':
                {
                    'to_install': [pkg for pkg in data.to_install],
                    'to_remove': [pkg for pkg in data.to_remove]
                },
            'dnf_conf':
                {
                     'allow_erasing': True,
                     'best': True,
                     'debugsolver': debugsolver,
                     'disable_repos': True,
                     'enable_repos': target_repoids,
                     'gpgcheck': False,
                     'platform_id': 'platform:el8',
                     'releasever': '8',
                     'test_flag': False,
                }
            }

        with NamedTemporaryFile() as data:
            json.dump(plugin_data, data)
            data.flush()
            run(dnf_command + [data.name], callback_raw=_logging_handler)

        self.produce(TransactionCompleted())
