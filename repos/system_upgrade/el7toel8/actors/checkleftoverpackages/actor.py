from leapp.actors import Actor
from leapp.libraries.common.rpms import get_installed_rpms
from leapp.models import InstalledUnsignedRPM, LeftoverPackages, RPM, TransactionCompleted
from leapp.tags import IPUWorkflowTag, RPMUpgradePhaseTag


class CheckLeftoverPackages(Actor):
    """
    Check if there are any RHEL 7 packages present after upgrade.

    Actor produces message containing these packages. Message is empty if there are no el7 package left.
    """

    name = 'check_leftover_packages'
    consumes = (TransactionCompleted, InstalledUnsignedRPM)
    produces = (LeftoverPackages,)
    tags = (RPMUpgradePhaseTag, IPUWorkflowTag)

    def process(self):
        LEAPP_PACKAGES = ['leapp', 'leapp-repository', 'snactor', 'leapp-repository-deps-el8', 'leapp-deps-el8',
                          'python2-leapp']
        installed_rpms = get_installed_rpms()
        if not installed_rpms:
            return

        to_remove = LeftoverPackages()
        unsigned = [pkg.name for pkg in next(self.consume(InstalledUnsignedRPM), InstalledUnsignedRPM()).items]

        for rpm in installed_rpms:
            rpm = rpm.strip()
            if not rpm:
                continue
            name, version, release, epoch, packager, arch, pgpsig = rpm.split('|')

            if 'el7' in release and name not in set(unsigned + LEAPP_PACKAGES):
                to_remove.items.append(RPM(
                    name=name,
                    version=version,
                    epoch=epoch,
                    packager=packager,
                    arch=arch,
                    release=release,
                    pgpsig=pgpsig
                ))

        self.produce(to_remove)
