import os
import json

from leapp.actors import Actor
from leapp.libraries.actor import preparetransaction
from leapp.models import FilteredRpmTransactionTasks, OSReleaseFacts, TargetRepositories
from leapp.models import UsedTargetRepositories, UsedTargetRepository
from leapp.tags import IPUWorkflowTag, DownloadPhaseTag


class PrepareUpgradeTransaction(Actor):
    name = 'prepare_upgrade_transaction'
    description = 'Actor for preparing upgrade transaction.'
    consumes = (OSReleaseFacts, FilteredRpmTransactionTasks, TargetRepositories)
    produces = (UsedTargetRepositories,)
    tags = (IPUWorkflowTag, DownloadPhaseTag,)

    def is_system_registered_and_attached(self):
        # TODO: put this to different actor and process it already during check
        # + phase
        # FIXME: no exception is caught, retcode is not checked
        out = preparetransaction.call(['subscription-manager', 'list', '--consumed'], split=True)
        for i in out:
            if i.startswith('SKU'):
                # if any SKU is consumed, return True; we cannot check more
                # now.
                return True
        return False

    def update_rhel_subscription(self, overlayfs_info):
        sys_var = ""
        for msg in self.consume(OSReleaseFacts):
            if msg.variant_id:
                sys_var = msg.variant_id
                break

        # Make sure Subscription Manager OS Release is unset
        cmd = ['subscription-manager', 'release', '--unset']
        _unused, error = preparetransaction.guard_container_call(
            overlayfs_info,
            cmd,
            guards=(preparetransaction.connection_guard(),)
        )
        if error:
            error.summary = 'Cannot remove version preference.'
            return error

        var_prodcert = {'server': '230.pem'}
        if sys_var not in var_prodcert:
            return preparetransaction.ErrorData(
                summary="Failed to to retrieve Product Cert file.",
                details="Product cert file not available for System Variant '{}'.".format(sys_var))

        prod_cert_path = self.get_file_path(var_prodcert[sys_var])
        for path in ('/etc/pki/product-default', '/etc/pki/product'):
            if not os.path.isdir(path):
                continue

            existing_certs = [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
            if not existing_certs:
                continue

            error = preparetransaction.copy_file_to_container(overlayfs_info, prod_cert_path, path)
            if error:
                return error

            # FIXME: it's removing all certs from /etc/pki/product - but we should remove only the
            # + EngID provided by a redhat-release-* rpm in the directory (Maybe another RH cert
            # + but we should not remove user's 3rd party certs (e.g. for custom repositories it
            # + would be problem later). Needs a little investigation here about the impact, even
            # + in the container.
            for cert in existing_certs:
                # FIXME: fails on insufficient permissions
                cmd = ['rm', '-f', cert]
                _unused, error = preparetransaction.guard_container_call(overlayfs_info, cmd)
                if error:
                    return error

        cmd = ['subscription-manager', 'refresh']
        _unused, error = preparetransaction.guard_container_call(
            overlayfs_info,
            cmd,
            guards=(preparetransaction.connection_guard(),)
        )
        return error

    def _setup_target_repos(self, overlayfs_info):
        """
        Setup target repositories.

        Set the list of UIDs that should be used for the upgrade of the system.
        In addition, it prepare repo file with custom repositories (in case
        they don't exist on the system already) and use them for the upgrade
        as well. The custom repositories should be persistent and enabled
        or disabled by default based on data in CustomTargetRepository models.

        Return ErrorData or None.
        """
        self.target_uids = []

        available_target_uids, error = preparetransaction.get_list_of_available_repo_uids(overlayfs_info)
        if error:
            return error

        # FIXME: check that required UIDs (baseos, appstream)
        # + or check that all required RHEL UIDs are available.
        if not available_target_uids or len(available_target_uids) < 2:
            return preparetransaction.ErrorData(
                summary='Cannot find required basic RHEL repositories.',
                details=('It is required to have RHEL repository on the system'
                         ' provided by the subscription-manager. Possibly you'
                         ' are missing a valid SKU for the target system or network'
                         ' connection failed. Check whether you the system is attached'
                         ' to the valid SKU providing target repositories.'))
        for target_repo in self.consume(TargetRepositories):
            for rhel_repo in target_repo.rhel_repos:
                if rhel_repo.uid in available_target_uids:
                    self.target_uids.append(rhel_repo.uid)
            for custom_repo in target_repo.custom_repos:
                # TODO: complete processing of custom repositories
                # HINT: now it will work only for custom repos that exist
                # + already on the system in a repo file
                # TODO: should check available_target_uids + additional custom repos
                # + outside of rhsm..
                # #if custom_repo.uid in available_target_uids:
                self.target_uids.append(custom_repo.uid)
        return None

    def produce_used_target_repos(self):
        """
        Produce list of used repositories

        We need to know exactly which repositories should be used inside
        the initramdisk. For this purpose, produce list of used repositories
        (just uids) to use same setup of the upgrade transaction as during
        this precalculation.
        """
        used_repos = []
        for used_uid in self.target_uids:
            used_repos.append(UsedTargetRepository(uid=used_uid))
        self.produce(UsedTargetRepositories(
            repos=used_repos
        ))

    def dnf_plugin_rpm_download(self, overlayfs_info):
        dnf_command = ['/usr/bin/dnf', 'rhel-upgrade', 'download']

        # get list of UIDs of target repositories that should be used for upgrade
        error = self._setup_target_repos(overlayfs_info)
        if error:
            return error
        if not self.target_uids:
            return preparetransaction.ErrorData(
                summary='Cannot find any required target repository.',
                details='The list of available required repositories is empty.')

        debugsolver = True if os.environ.get('LEAPP_DEBUG', '0') == '1' else False

        error = preparetransaction.mount_dnf_cache(overlayfs_info)
        if error:
            return error

        data = next(self.consume(FilteredRpmTransactionTasks), FilteredRpmTransactionTasks())

        plugin_data = {
            'pkgs_info': {
                'local_rpms': [pkg for pkg in data.local_rpms],
                'to_install': [pkg for pkg in data.to_install],
                'to_remove': [pkg for pkg in data.to_remove]
            },
            'dnf_conf': {
                'allow_erasing': True,
                'best': True,
                'debugsolver': debugsolver,
                'disable_repos': True,
                'enable_repos': self.target_uids,
                'gpgcheck': False,
                'platform_id': 'platform:el8',
                'releasever': '8',
                'test_flag': True,
            }
        }

        with open(os.path.join(overlayfs_info.merged, 'var', 'lib', 'leapp', 'dnf-plugin-data.txt'), 'w+') as data:
            json.dump(plugin_data, data)
            data.flush()

        # FIXME: fails on insufficient permissions
        cmd = ['--', '/bin/bash', '-c', ' '.join(dnf_command + ['/var/lib/leapp/dnf-plugin-data.txt'])]
        _unused, error = preparetransaction.guard_container_call(
            overlayfs_info, cmd,
            guards=(preparetransaction.connection_guard(), preparetransaction.space_guard()))

        if os.environ.get('LEAPP_DEBUG', '0') == '1':
            # We want the debug data available where we would expect it usually.
            cmd = ['rm', '-rf', os.path.join('/tmp', 'download-debugdata')]
            _unused, dbg_error = preparetransaction.guard_call(cmd)
            if dbg_error:
                preparetransaction.produce_warning(dbg_error, summary='Cannot remove old debugdata.')

            cmd = ['cp', '-a', os.path.join(overlayfs_info.merged, 'debugdata'), '/tmp/download-debugdata']
            _unused, dbg_error = preparetransaction.guard_call(cmd)
            if dbg_error:
                preparetransaction.produce_warning(dbg_error, summary='Cannot copy new debugdata.')

        if error:
            umount_error = preparetransaction.umount_dnf_cache(overlayfs_info)
            if umount_error:
                preparetransaction.produce_error(umount_error)
            return error

        return preparetransaction.umount_dnf_cache(overlayfs_info)

    def process(self):
        container_root = os.getenv('LEAPP_CONTAINER_ROOT', '/tmp/leapp-overlay')
        error_flag = False

        if not self.is_system_registered_and_attached():
            error = preparetransaction.ErrorData(
                summary='The system is not registered or subscribed.',
                details=('The system has to be registered and subscribed to be able'
                         ' to proceed the upgrade. Register your system with the'
                         ' subscription-manager tool and attach'
                         ' it to proper SKUs to be able to proceed the upgrade.'))
            preparetransaction.produce_error(error)
            return

        # TODO: Find a better place where to run this (perhaps even gate this behind user prompt/question)
        # FIXME: fails on insufficient permissions
        cmd = ['/usr/bin/dnf', 'clean', 'all']
        _unused, error = preparetransaction.guard_call(cmd)
        if error:
            preparetransaction.produce_error(error, summary='Cannot perform dnf cleanup.')
            return

        # prepare container #
        # TODO: wrap in one function (create ofs dirs, mount), or even context
        #       manager (enter -> create dirs, mount; exit -> umount)?
        ofs_info, error = preparetransaction.create_overlayfs_dirs(container_root)
        if not ofs_info:
            preparetransaction.produce_error(error)
            return

        error = preparetransaction.mount_overlayfs(ofs_info)
        if error:
            preparetransaction.produce_error(error)
            preparetransaction.remove_overlayfs_dirs(container_root)
            return

        # switch EngID to use RHEL 8 subscriptions #
        cmd = ['subscription-manager', 'release']
        prev_rhsm_release, error = preparetransaction.guard_call(
            cmd, guards=(preparetransaction.connection_guard(),))
        if error:
            preparetransaction.produce_error(error, summary='Cannot get release setting.')
            return
        prev_rhsm_release = prev_rhsm_release[0]

        error = self.update_rhel_subscription(ofs_info)

        if not error:
            dnfplugin_spath = self.get_file_path('rhel_upgrade.py')
            dnfplugin_dpath = '/lib/python2.7/site-packages/dnf-plugins'

            error = preparetransaction.copy_file_to_container(ofs_info, dnfplugin_spath, dnfplugin_dpath)
            if error:
                return error

        error = self.dnf_plugin_rpm_download(ofs_info)

        if not error:
            error = preparetransaction.copy_file_from_container(
                ofs_info,
                '/etc/yum.repos.d/redhat.repo',
                '/etc/yum.repos.d/',
                'redhat.repo.upgrade',
            )

        if error:
            preparetransaction.produce_error(error)
            error_flag = True

        # If Subscription Manager OS Release was set before, make sure we do not change it
        if 'Release:' in prev_rhsm_release:
            release = prev_rhsm_release.split(':')[1].strip()
            cmd = ['subscription-manager', 'release', '--set', release]
            _unused, error = preparetransaction.guard_call(cmd, guards=(preparetransaction.connection_guard(),))
            if error:
                preparetransaction.produce_error(error, summary='Cannot set minor release version.')
                error_flag = True

        # clean #
        error = preparetransaction.umount_overlayfs(ofs_info)
        if error:
            preparetransaction.produce_error(error)
            error_flag = True

        preparetransaction.remove_overlayfs_dirs(container_root)

        # produce msg for upgrading actor
        if not error_flag:
            self.produce_used_target_repos()
