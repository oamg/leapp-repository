# plugin inspired by "system_upgrade.py" from rpm-software-management

import json

import dnf
import dnf.cli

CMDS = ['download', 'upgrade', 'check']


class RhelUpgradeCommand(dnf.cli.Command):
    aliases = ('rhel-upgrade',)
    summary = ("Plugin for upgrading to the next RHEL major release")

    def __init__(self, cli):
        super(RhelUpgradeCommand, self).__init__(cli)
        self.plugin_data = {}
        self.pkgs_notfound = []

    @staticmethod
    def set_argparser(parser):
        parser.add_argument('tid', nargs=1, choices=CMDS,
                            metavar="[%s]" % "|".join(CMDS))
        parser.add_argument('filename')

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
                repo.skip_if_unavailable = False
                repo.enable()

    def run(self):
        self.base.add_remote_rpms(self.plugin_data['pkgs_info']['local_rpms'])

        for pkg_spec in self.plugin_data['pkgs_info']['to_remove']:
            try:
                self.base.remove(pkg_spec)
            except dnf.exceptions.MarkingError:
                self.pkgs_notfound.append(pkg_spec)

        for pkg_spec in self.plugin_data['pkgs_info']['to_install']:
            try:
                self.base.install(pkg_spec)
            except dnf.exceptions.MarkingError:
                self.pkgs_notfound.append(pkg_spec)

        q = self.base.sack.query().installed()
        for pkg in q:
            if pkg.name not in (self.plugin_data['pkgs_info']['to_install']
                                + self.plugin_data['pkgs_info']['to_remove']):
                self.base.upgrade(pkg.name)

        self.base.distro_sync()
        if not self.cli.demands.resolving:
            self.base.resolve(allow_erasing=self.cli.demands.allow_erasing)
            self.base.do_transaction()


class RhelUpgradePlugin(dnf.Plugin):
    name = 'rhel-upgrade'

    def __init__(self, base, cli):
        super(RhelUpgradePlugin, self).__init__(base, cli)
        if cli:
            cli.register_command(RhelUpgradeCommand)
