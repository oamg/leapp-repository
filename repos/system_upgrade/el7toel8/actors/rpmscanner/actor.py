from leapp.actors import Actor
from leapp.libraries.actor.rpmscanner import get_package_repository_data, map_installed_rpms_to_modules
from leapp.libraries.common.rpms import get_installed_rpms
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

    def process(self):
        output = get_installed_rpms()
        pkg_repos = get_package_repository_data()
        rpm_streams = map_installed_rpms_to_modules()

        result = InstalledRPM()
        for entry in output:
            entry = entry.strip()
            if not entry:
                continue
            name, version, release, epoch, packager, arch, pgpsig = entry.split('|')
            repository = pkg_repos.get(name, '')
            rpm_key = (name, version, release, arch)
            module, stream = rpm_streams.get(rpm_key, (None, None))
            result.items.append(RPM(
                name=name,
                version=version,
                epoch=epoch,
                packager=packager,
                arch=arch,
                release=release,
                pgpsig=pgpsig,
                repository=repository,
                module=module,
                stream=stream))
        self.produce(result)
