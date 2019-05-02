import os
import json

from leapp.actors import Actor
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import preparetransaction, xinitramgen
from leapp.libraries.stdlib import CalledProcessError
from leapp.models import FilteredRpmTransactionTasks, OSReleaseFacts, TargetRepositories
from leapp.models import XFSPresence, UsedTargetRepositories, UsedTargetRepository, BootContent
from leapp.tags import IPUWorkflowTag, DownloadPhaseTag


class PrepareUpgradeTransaction(Actor):
    """
    Actor responsible for executing multiple tasks to setup upgrade transaction.

    Between the necessary steps to calculate and prepare DNF upgrade transaction, this actor will
    check if system has a valid subscription and move to inside a new created container using
    overlayfs. Once inside this container, necessary changes will be done on existing subscription,
    a DNF upgrade transaction will be calculated and all necessary packages will be downloaded to
    be used on real upgrade.
    """

    name = 'prepare_upgrade_transaction'
    consumes = (OSReleaseFacts, FilteredRpmTransactionTasks, TargetRepositories, XFSPresence)
    produces = (UsedTargetRepositories, BootContent)
    tags = (IPUWorkflowTag, DownloadPhaseTag,)

    def is_system_registered_and_attached(self):
        # TODO: put this to different actor and process it already during check
        # + phase
        # FIXME: no exception is caught, retcode is not checked
        out = preparetransaction.run(['subscription-manager', 'list', '--consumed'], split=True)
        for i in out['stdout']:
            if i.startswith('SKU'):
                # if any SKU is consumed, return True; we cannot check more
                # now.
                return True
        return False

    def get_rhsm_system_release(self):
        """
        Get system release set by RHSM or None on error.
        """
        cmd = ['subscription-manager', 'release']
        prev_rhsm_release, error = preparetransaction.guard_call(
            cmd, guards=(preparetransaction.connection_guard(),))
        if error:
            preparetransaction.produce_error(error, summary='Cannot get release setting.')
            return None
        return prev_rhsm_release[0]

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

        var_prodcert = {'server': '479.pem'}
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

        Set the list of repos IDs that should be used for the upgrade of the system.
        In addition, it prepare repo file with custom repositories (in case
        they don't exist on the system already) and use them for the upgrade
        as well. The custom repositories should be persistent and enabled
        or disabled by default based on data in CustomTargetRepository models.

        Return ErrorData or None.
        """
        self.target_repoids = []
        skip_rhsm = os.getenv('LEAPP_DEVEL_SKIP_RHSM', '0') == '1'

        # TODO: skip_rhsm will work for now, but later it should be refactored better
        available_target_repoids = set()
        if not skip_rhsm:
            available_target_repoids, error = preparetransaction.get_list_of_available_repoids(overlayfs_info)
            if error:
                return error

            # FIXME: check that required repo IDs (baseos, appstream)
            # + or check that all required RHEL repo IDs are available.
            if not available_target_repoids or len(available_target_repoids) < 2:
                return preparetransaction.ErrorData(
                    summary='Cannot find required basic RHEL repositories.',
                    details=('It is required to have RHEL repository on the system'
                             ' provided by the subscription-manager. Possibly you'
                             ' are missing a valid SKU for the target system or network'
                             ' connection failed. Check whether you the system is attached'
                             ' to the valid SKU providing target repositories.'))
        for target_repo in self.consume(TargetRepositories):
            for rhel_repo in target_repo.rhel_repos:
                if rhel_repo.repoid in available_target_repoids:
                    self.target_repoids.append(rhel_repo.repoid)
            for custom_repo in target_repo.custom_repos:
                # TODO: complete processing of custom repositories
                # HINT: now it will work only for custom repos that exist
                # + already on the system in a repo file
                # TODO: should check available_target_repoids + additional custom repos
                # + outside of rhsm..
                # #if custom_repo.repoid in available_target_repoids:
                self.target_repoids.append(custom_repo.repoid)
        return None

    def produce_used_target_repos(self):
        """
        Produce list of used repositories

        We need to know exactly which repositories should be used inside
        the initramdisk. For this purpose, produce list of used repositories
        (just repoids) to use same setup of the upgrade transaction as during
        this precalculation.
        """
        used_repos = []
        for used_repoid in self.target_repoids:
            used_repos.append(UsedTargetRepository(repoid=used_repoid))
        self.produce(UsedTargetRepositories(
            repos=used_repos
        ))

    def dnf_plugin_rpm_download(self, overlayfs_info):
        dnf_command = ['/usr/bin/dnf', 'rhel-upgrade', 'download']

        # get list of repo IDs of target repositories that should be used for upgrade
        error = self._setup_target_repos(overlayfs_info)
        if error:
            return error
        if not self.target_repoids:
            return preparetransaction.ErrorData(
                summary='Cannot find any required target repository.',
                details='The list of available required repositories is empty.')

        debugsolver = True if os.environ.get('LEAPP_DEBUG', '0') == '1' else False

        yum_script_path = self.get_tool_path('handleyumconfig')
        cmd = ['--', '/bin/bash', '-c', yum_script_path]
        _unused, error = preparetransaction.guard_container_call(overlayfs_info, cmd)
        if error:
            return error

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
                'enable_repos': self.target_repoids,
                'gpgcheck': False,
                'platform_id': 'platform:el8',
                'releasever': '8',
                'test_flag': True,
            }
        }

        with open(os.path.join(overlayfs_info.merged, 'var', 'lib', 'leapp', 'dnf-plugin-data.txt'), 'w+') as data:
            json.dump(plugin_data, data)
            data.flush()

        copy_error = preparetransaction.copy_file_from_container(
            overlayfs_info,
            '/var/lib/leapp/dnf-plugin-data.txt',
            '/var/log/leapp/',
            'dnf-plugin-data.txt',
        )

        if copy_error:
            preparetransaction.produce_warning(copy_error)

        # FIXME: fails on insufficient permissions
        cmd = ['--', '/bin/bash', '-c', ' '.join(dnf_command + ['/var/lib/leapp/dnf-plugin-data.txt'])]
        _unused, error = preparetransaction.guard_container_call(
            overlayfs_info, cmd,
            guards=(preparetransaction.connection_guard(), preparetransaction.space_guard()), print_output=True)

        if os.environ.get('LEAPP_DEBUG', '0') == '1':
            # We want the debug data available where we would expect it usually.
            debug_data_path = '/var/log/leapp/dnf-debugdata/'

            # The debugdata is a folder generated by dnf when using the --debugsolver dnf option. We switch on the
            # debug_solver dnf config parameter in our rhel-upgrade dnf plugin when LEAPP_DEBUG env var set to 1.
            cmd = ['cp', '-a', os.path.join(overlayfs_info.merged, 'debugdata'), debug_data_path]
            _unused, dbg_error = preparetransaction.guard_call(cmd)
            if dbg_error:
                preparetransaction.produce_warning(dbg_error, summary='Cannot copy new debugdata.')

        if error:
            umount_error = preparetransaction.umount_dnf_cache(overlayfs_info)
            if umount_error:
                preparetransaction.produce_error(umount_error)
            return error

        try:
            el8userspace = '/var/lib/leapp/el8target'
            # Prepare el8 userspace with help of the overlay system
            xinitramgen.prepare_el8_userspace(overlayfs_info, el8userspace, self.target_repoids)
            # Dracut invocation
            xinitramgen.generate_initram_disk(el8userspace)
            # Artifacts moving (kernel/initram disk)
            xinitramgen.copy_boot_files(el8userspace)
            # clean up - Not used at the moment
            xinitramgen.remove_userspace(el8userspace)
        except Exception as e:
            self.log.error("Caught an exception", exc_info=True)
            if isinstance(e, StopActorExecutionError):
                raise
            # Raise for other problems
            raise StopActorExecutionError(
                message='Preparing initram disk failed with an unexpected error',
                details=str(e)
            )
        finally:
            return preparetransaction.umount_dnf_cache(overlayfs_info)

    def process(self):
        skip_rhsm = os.getenv('LEAPP_DEVEL_SKIP_RHSM', '0') == '1'
        mounts_dir = os.getenv('LEAPP_CONTAINER_ROOT', '/var/lib/leapp/scratch')
        container_root = os.path.join(mounts_dir, 'mounts')
        error_flag = False

        if skip_rhsm:
            self.log.warning("LEAPP_DEVEL_SKIP_RHSM has been used. The upgrade is unsupported.")

        if not skip_rhsm and not self.is_system_registered_and_attached():
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
        xfs_presence = next(self.consume(XFSPresence), XFSPresence())
        if xfs_presence.present and xfs_presence.without_ftype:
            error = preparetransaction.create_disk_image(mounts_dir)
            if error:
                self.produce_error(error)

        ofs_info, error = preparetransaction.create_overlayfs_dirs(container_root)
        if not ofs_info:
            preparetransaction.produce_error(error)
            return

        error = preparetransaction.mount_overlayfs(ofs_info)
        if error:
            preparetransaction.produce_error(error)
            preparetransaction.remove_overlayfs_dirs(container_root)
            preparetransaction.remove_disk_image(mounts_dir)
            return

        prev_rhsm_release = None
        if not skip_rhsm:
            prev_rhsm_release = self.get_rhsm_system_release()
            if prev_rhsm_release is None:
                # TODO: error is produced inside - will be refactored later
                # with the whole actor
                return
            # switch EngID to use RHEL 8 subscriptions #
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
        if not skip_rhsm and 'Release:' in prev_rhsm_release:
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
        preparetransaction.remove_disk_image(mounts_dir)

        # produce msg for upgrading actor
        if not error_flag:
            self.produce_used_target_repos()
