# plugin inspired by "system_upgrade.py" from rpm-software-management
from __future__ import print_function

import json
import logging
import sys

import dnf
import dnf.cli
import dnf.module.module_base

CMDS = ['check', 'download', 'dry-run', 'upgrade']
"""
Basic subcommands for the plugin.

    check    -> check we are able to calculate the DNF transaction using
                only the YUM/DNF repositories metadata (no packages downloaded)
    download -> calculate the transaction, download all packages and test
                the transaction is duable using data contained in RPMs
                (include search for file conflicts, disk space, ...)
    dry-run  -> test the transaction again with the cached content (including
                the downloaded RPMs; it is subset of the download cmd)(
                  BZ: 1976932 - not enough space on disk,
                  PR: https://github.com/oamg/leapp-repository/pull/734
                )
    upgrade  -> perform the DNF transaction using the cached data only
"""


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

    def _process_entities(self, entities, op, entity_name):
        """
        Adds list of packages for given operation to the transaction
        """
        entities_notfound = []

        for spec in entities:
            try:
                op(spec)
            except dnf.exceptions.MarkingError:
                if isinstance(spec, (list, tuple)):
                    entities_notfound.extend(spec)
                else:
                    entities_notfound.append(spec)
        if entities_notfound:
            err_str = ('{} marked by Leapp to {} not found '
                       'in repositories metadata: '.format(entity_name, op.__name__) + ' '.join(entities_notfound))
            print('Warning: ' + err_str, file=sys.stderr)

    def _save_aws_region(self, region):
        self.plugin_data['rhui']['aws']['region'] = region
        with open(self.opts.filename, 'w+') as fo:
            json.dump(self.plugin_data, fo, sort_keys=True, indent=2)

    def _read_aws_region(self, repo):
        region = None
        if repo.baseurl:
            # baseurl is tuple (changed by Amazon-id plugin)
            # here we take just the first baseurl as the REGION will be same for all of them
            region = repo.baseurl[0].split('.', 2)[1]
        elif repo.mirrorlist:
            region = repo.mirrorlist.split('.', 2)[1]
        if not region:
            print('Could not read AWS REGION from either baseurl or mirrorlist', file=sys.stderr)
            sys.exit(1)
        return region

    def _fix_rhui_url(self, repo, region):
        if repo.baseurl:
            repo.baseurl = tuple(
                url.replace('REGION', region, 1) for url in repo.baseurl
            )
        elif repo.mirrorlist:
            repo.mirrorlist = repo.mirrorlist.replace('REGION', region, 1)
        else:
            raise dnf.exceptions.RepoError("RHUI repository %s does not have an url" % repo.name)
        return repo

    def pre_configure(self):
        with open(self.opts.filename) as fo:
            self.plugin_data = json.load(fo)
        # There is an issue that ignores releasever value if it is set at configure
        self.base.conf.releasever = self.plugin_data['dnf_conf']['releasever']

    def configure(self):

        on_aws = self.plugin_data['rhui']['aws']['on_aws']
        self.cli.demands.root_user = True
        self.cli.demands.resolving = self.opts.tid[0] != 'check'
        self.cli.demands.available_repos = True
        self.cli.demands.sack_activation = True
        self.cli.demands.cacheonly = self.opts.tid[0] in ['dry-run', 'upgrade']
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
        if self.plugin_data['dnf_conf']['test_flag'] and self.opts.tid[0] in ['download', 'dry-run']:
            self.base.conf.tsflags.append("test")

        enabled_repos = self.plugin_data['dnf_conf']['enable_repos']
        self.base.repos.all().disable()

        aws_region = None

        for repo in self.base.repos.all():
            if repo.id in enabled_repos:
                repo.skip_if_unavailable = False
                if not self.base.conf.gpgcheck:
                    repo.gpgcheck = False
                repo.enable()
                if self.opts.tid[0] == 'download' and on_aws:
                    # during the upgrade phase we has to disable "Amazon-id" plugin as we do not have networking
                    # in initramdisk (yet, but we probably do not want it to do anything anyway as we already have
                    # packages downloaded and cached). However, when we disable it, the plugin cannot substitute
                    # "REGION" placeholder in mirrorlist url and consequently we cannot identify a correct cache
                    # folder in "/var/cache/dnf" as it has different digest calculated based on already substituted
                    # placeholder.
                    # E.g
                    # "https://rhui3.REGION.aws.ce.redhat.com" becomes "https://rhui3.eu-central-1.aws.ce.redhat.com"
                    #
                    # region should be same for all repos so we are fine to collect it from
                    # the last one
                    aws_region = self._read_aws_region(repo)
                if self.opts.tid[0] in ['dry-run', 'upgrade'] and on_aws:
                    aws_region = self.plugin_data['rhui']['aws']['region']
                    if aws_region:
                        repo = self._fix_rhui_url(repo, aws_region)

        if aws_region and self.opts.tid[0] == 'download':
            self._save_aws_region(aws_region)

    def run(self):
        # takes local rpms, creates Package objects from them, and then adds them to the sack as virtual repository
        local_rpm_objects = self.base.add_remote_rpms(self.plugin_data['pkgs_info']['local_rpms'])

        for pkg in local_rpm_objects:
            self.base.package_install(pkg)

        module_base = dnf.module.module_base.ModuleBase(self.base)

        # Module tasks
        modules_to_enable = self.plugin_data['pkgs_info'].get('modules_to_enable', ())

        available_modules_to_enable = []
        unavailable_modules = []
        for module in modules_to_enable:
            matching_modules, dummy_nsvcap = module_base.get_modules(module)
            target_bucket = available_modules_to_enable if matching_modules else unavailable_modules
            target_bucket.append(module)

        if unavailable_modules:
            dnf_plugin_logger = logging.getLogger('dnf.plugin')
            msg = 'The following modules were requested to be enabled, but they are unavailable: %s'
            dnf_plugin_logger.warning(msg, ', '.join(unavailable_modules))

        # Package tasks
        to_install = self.plugin_data['pkgs_info']['to_install']
        to_remove = self.plugin_data['pkgs_info']['to_remove']
        to_upgrade = self.plugin_data['pkgs_info']['to_upgrade']

        # Modules to enable
        self._process_entities(entities=[available_modules_to_enable],
                               op=module_base.enable,
                               entity_name='Module stream')

        # Packages to be removed
        self._process_entities(entities=to_remove, op=self.base.remove, entity_name='Package')
        # Packages to be installed
        self._process_entities(entities=to_install, op=self.base.install, entity_name='Package')
        # Packages to be upgraded
        self._process_entities(entities=to_upgrade, op=self.base.upgrade, entity_name='Package')
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
