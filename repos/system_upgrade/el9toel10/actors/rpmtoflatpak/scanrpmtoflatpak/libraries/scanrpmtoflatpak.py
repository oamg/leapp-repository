from leapp.libraries.common.config import get_target_distro_id
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, FlatpakMigrationPackage, RpmToFlatpakFacts

# Maps RPM package names to their corresponding flatpak-preinstall package names.
# The preinstall package is installed on the target system; flatpak preinstall is
# then called explicitly by migraterpmtoflatpak to pull in the Flatpak from the
# required remote as defined in the preinstall configuration.
_RPM_TO_FLATPAK_MAP = {
    'firefox': 'redhat-flatpak-preinstall-firefox',
    'thunderbird': 'redhat-flatpak-preinstall-thunderbird',
}


def _get_packages_to_migrate():
    packages = []
    for rpm_name, preinstall_pkg in _RPM_TO_FLATPAK_MAP.items():
        if has_package(DistributionSignedRPM, rpm_name):
            packages.append(FlatpakMigrationPackage(
                rpm_name=rpm_name,
                preinstall_pkg=preinstall_pkg,
            ))
            api.current_logger().debug(
                'Package {} is installed and it should be migrated to Flatpak via {}'.format(
                    rpm_name, preinstall_pkg
                )
            )
    return packages


def process():
    # The Flatpak applications and the redhat-flatpak-preinstall-* packages are
    # delivered only for RHEL. On the other EL distributions there is nothing to
    # migrate (and the preinstall packages are not available there), so skip the
    # scan completely.
    target_distro = get_target_distro_id()
    if target_distro != 'rhel':
        api.current_logger().debug(
            'Skipping the RPM-to-Flatpak migration scan: the Flatpak applications are '
            'delivered only on RHEL, but the target system is {}.'.format(target_distro)
        )
        return

    packages = _get_packages_to_migrate()
    api.produce(RpmToFlatpakFacts(packages=packages))
