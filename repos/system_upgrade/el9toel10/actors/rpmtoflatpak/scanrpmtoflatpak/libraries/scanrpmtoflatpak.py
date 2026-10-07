from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, FlatpakMigrationPackage, RpmToFlatpakFacts

_FLATPAK_PKG = 'flatpak'

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
                'Package {} is installed and will be migrated to Flatpak via {}'.format(
                    rpm_name, preinstall_pkg
                )
            )
    return packages


def process():
    packages = _get_packages_to_migrate()
    api.produce(RpmToFlatpakFacts(packages=packages))
