from leapp.actors import Actor
from leapp.libraries import stdlib
from leapp.libraries.common import rhsm
from leapp.libraries.common.rpms import get_installed_rpms
from leapp.models import LeftoverPackages, RemovedPackages, RPM
from leapp.reporting import Report
from leapp.tags import ExperimentalTag, IPUWorkflowTag, RPMUpgradePhaseTag


class RemoveLeftoverPackages(Actor):
    """
    Remove el7 packages left on the system after the upgrade to RHEL 8.

    Removal of el7 packages is necessary in order to keep the machine in supported state.
    Actor generates report telling users what packages have been removed.
    """

    name = 'remove_leftover_packages'
    consumes = (LeftoverPackages, )
    produces = (Report, RemovedPackages)
    tags = (RPMUpgradePhaseTag, IPUWorkflowTag, ExperimentalTag)

    def process(self):
        leftover_packages = next(self.consume(LeftoverPackages), LeftoverPackages())
        if not leftover_packages.items:
            self.log.info('No leftover packages, skipping...')
            return

        installed_rpms = get_installed_rpms()

        to_remove = ['-'.join([pkg.name, pkg.version, pkg.release]) for pkg in leftover_packages.items]
        cmd = ['dnf', 'remove', '-y', '--noautoremove'] + to_remove
        if rhsm.skip_rhsm():
            # ensure we don't use suscription-manager when it should be skipped
            cmd += ['--disableplugin', 'subscription-manager']
        try:
            stdlib.run(cmd)
        except stdlib.CalledProcessError:
            error = 'Failed to remove packages: {}'.format(', '.join(to_remove))
            self.log.error(error)
            return

        removed_packages = RemovedPackages()
        removed = list(set(installed_rpms) - set(get_installed_rpms()))
        for pkg in removed:
            name, version, release, epoch, packager, arch, pgpsig = pkg.split('|')
            removed_packages.items.append(RPM(
                name=name,
                version=version,
                epoch=epoch,
                packager=packager,
                arch=arch,
                release=release,
                pgpsig=pgpsig
            ))
        self.produce(removed_packages)
