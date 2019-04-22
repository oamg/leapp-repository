import yum

from leapp.actors import Actor
from leapp.libraries.common.rpms import get_installed_rpms
from leapp.libraries.stdlib import run
from leapp.models import InstalledRPM, RPM
from leapp.tags import IPUWorkflowTag, FactsPhaseTag


class RpmScanner(Actor):
    """
    Provides data about installed RPM Packages.

    After collecting data from RPM query, a message with relevant data will be produced.
    """

    name = 'rpm_scanner'
    consumes = ()
    produces = (InstalledRPM,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def get_package_repository_data(self):
        """ Return dictionary mapping package name with repository from which it was installed """
        yum_base = yum.YumBase()
        pkg_repos = {}
        for pkg in yum_base.doPackageLists().installed:
            pkg_repos[pkg.name] = pkg.ui_from_repo.lstrip('@')

        return pkg_repos


    def process(self):
        output = get_installed_rpms()
        pkg_repos = self.get_package_repository_data()

        result = InstalledRPM()
        for entry in output:
            entry = entry.strip()
            if not entry:
                continue
            name, version, release, epoch, packager, arch, pgpsig = entry.split('|')
            repository = pkg_repos.get(name, '')
            result.items.append(RPM(
                name=name,
                version=version,
                epoch=epoch,
                packager=packager,
                arch=arch,
                release=release,
                pgpsig=pgpsig,
                repository=repository))
        self.produce(result)
