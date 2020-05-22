# plugin inspired by "system_upgrade.py" from rpm-software-management
from __future__ import print_function

import json
import sys

import dnf
import dnf.cli

CMDS = ['download', 'upgrade', 'check']


class DoNotDownload(Exception):
    pass


def _do_not_download_packages(packages, progress=None, total=None):
    raise DoNotDownload()


class RhelUpgradeCommand(dnf.cli.Command):
    aliases = ('rhel-upgrade',)
    summary = ("Plugin for upgrading to the next RHEL major release")

    def __init__(self, cli):
        super(RhelUpgradeCommand, self).__init__(cli)
        self.plugin_data = {}

    @staticmethod
    def set_argparser(parser):
        parser.add_argument('tid', nargs=1, choices=CMDS,
                            metavar="[%s]" % "|".join(CMDS))
        parser.add_argument('filename')

    def _process_packages(self, pkg_set, op):
        '''
        Adds list of packages for given operation to the transaction
        '''
        pkgs_notfound = []

        for pkg_spec in pkg_set:
            try:
                op(pkg_spec)
            except dnf.exceptions.MarkingError:
                pkgs_notfound.append(pkg_spec)
        if pkgs_notfound:
            err_str = ('Packages marked by Leapp for {} not found '
                       'in repositories metadata: '.format(op.__name__) + ' '.join(pkgs_notfound))
            print('Warning: ' + err_str, file=sys.stderr)

    def pre_configure(self):
        with open(self.opts.filename) as fo:
            self.plugin_data = json.load(fo)
        # There is an issue that ignores releasever value if it is set at configure
        self.base.conf.releasever = self.plugin_data['dnf_conf']['releasever']

    def configure(self):
        self.cli.demands.root_user = True
        self.cli.demands.resolving = self.opts.tid[0] != 'check'
        self.cli.demands.available_repos = True
        self.cli.demands.sack_activation = True
        self.cli.demands.cacheonly = self.opts.tid[0] == 'upgrade'
        self.cli.demands.allow_erasing = self.plugin_data['dnf_conf']['allow_erasing']
        self.base.conf.protected_packages = []
        self.base.conf.best = self.plugin_data['dnf_conf']['best']
        self.base.conf.assumeyes = True
        self.base.conf.gpgcheck = self.plugin_data['dnf_conf']['gpgcheck']
        self.base.conf.debug_solver = self.plugin_data['dnf_conf']['debugsolver']
        self.base.conf.module_platform_id = self.plugin_data['dnf_conf']['platform_id']
        installroot = self.plugin_data['dnf_conf'].get('installroot')
        if installroot:
            self.base.conf.installroot = installroot
        if self.plugin_data['dnf_conf']['test_flag'] and self.opts.tid[0] == 'download':
            self.base.conf.tsflags.append("test")

        enabled_repos = self.plugin_data['dnf_conf']['enable_repos']
        self.base.repos.all().disable()
        for repo in self.base.repos.all():
            if repo.id in enabled_repos:
                if self.opts.tid[0] == 'upgrade':
                    # super ugly POC hardcore
                    # during the upgrade phase we has to disable "Amazon-id" plugin as we do not have networking in initramdisk (and we probably do not want it
                    # to do anything anyway as we already have packages downloaded and cached). However, when we disable it, the plugin cannot substitute "REGION" placeholder
                    # in mirrorlist url and consequently we cannot identify a correct cache folder in /var/cache/dnf as it has different digest calculated based on already 
                    # substituted placeholder. E.g:
                    #
                    # "https://rhui3.REGION.aws.ce.redhat.com" becames "https://rhui3.eu-central-1.aws.ce.redhat.com"
                    #
                    # we could solve this hardcode by updating "dnf-plugin-data.txt" during the download phase with the proper substituted mirrorlist
                    if repo.id == 'rhel-8-appstream-rhui-rpms':
                        repo.mirrorlist = 'https://rhui3.eu-central-1.aws.ce.redhat.com/pulp/mirror/content/dist/rhel8/rhui/8/x86_64/appstream/os'
                    if repo.id == 'rhel-8-appstream-rhui-source-rpms':
                        repo.mirrorlist = 'https://rhui3.eu-central-1.aws.ce.redhat.com/pulp/mirror/content/dist/rhel8/rhui/8/x86_64/appstream/source/SRPMS'
                    if repo.id == 'rhel-8-appstream-rhui-debug-rpms':
                       repo.mirrorlist = 'https://rhui3.eu-central-1.aws.ce.redhat.com/pulp/mirror/content/dist/rhel8/rhui/8/x86_64/appstream/debug'
                    if repo.id == 'rhel-8-baseos-rhui-rpms':
                       repo.mirrorlist = 'https://rhui3.eu-central-1.aws.ce.redhat.com/pulp/mirror/content/dist/rhel8/rhui/8/x86_64/baseos/os'
                    if repo.id == 'rhel-8-baseos-rhui-source-rpms':
                       repo.mirrorlist = 'https://rhui3.eu-central-1.aws.ce.redhat.com/pulp/mirror/content/dist/rhel8/rhui/8/x86_64/baseos/source/SRPMS'
                    if repo.id == 'rhel-8-baseos-rhui-debug-rpms':
                       repo.mirrorlist = 'https://rhui3.eu-central-1.aws.ce.redhat.com/pulp/mirror/content/dist/rhel8/rhui/8/x86_64/baseos/debug'
                    if repo.id == 'rhui-client-config-server-8':
                       repo.mirrorlist = 'https://rhui3.eu-central-1.aws.ce.redhat.com/pulp/mirror/protected/rhui-client-config/rhel/server/8/x86_64/os'
                repo.skip_if_unavailable = False
                if not self.base.conf.gpgcheck:
                    repo.gpgcheck = False
                repo.enable()

    def run(self):
        # takes local rpms, creates Package objects from them, and then adds them to the sack as virtual repository
        local_rpm_objects = self.base.add_remote_rpms(self.plugin_data['pkgs_info']['local_rpms'])

        for pkg in local_rpm_objects:
            self.base.package_install(pkg)

        to_install = self.plugin_data['pkgs_info']['to_install']
        to_remove = self.plugin_data['pkgs_info']['to_remove']
        to_upgrade = self.plugin_data['pkgs_info']['to_upgrade']

        # Packages to be removed
        self._process_packages(to_remove, self.base.remove)
        # Packages to be installed
        self._process_packages(to_install, self.base.install)
        # Packages to be upgraded
        self._process_packages(to_upgrade, self.base.upgrade)

        self.base.distro_sync()

        if self.opts.tid[0] == 'check':
            try:
                self.base.resolve(allow_erasing=self.cli.demands.allow_erasing)
            except dnf.exceptions.DepsolveError as e:
                print('Transaction check: ', file=sys.stderr)
                print(str(e), file=sys.stderr)
                raise

            # We are doing this to avoid downloading the packages in the check phase
            self.base.download_packages = _do_not_download_packages
            try:
                displays = []
                if self.cli.demands.transaction_display is not None:
                    displays.append(self.cli.demands.transaction_display)
                self.base.do_transaction(display=displays)
            except DoNotDownload:
                print('Check completed.')


class RhelUpgradePlugin(dnf.Plugin):
    name = 'rhel-upgrade'

    def __init__(self, base, cli):
        super(RhelUpgradePlugin, self).__init__(base, cli)
        if cli:
            cli.register_command(RhelUpgradeCommand)
