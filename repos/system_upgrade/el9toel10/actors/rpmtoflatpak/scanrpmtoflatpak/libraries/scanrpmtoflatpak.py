from leapp.libraries.common.rhsm import skip_rhsm
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, FlatpakMigrationPackage, RHSMInfo, RpmToFlatpakFacts

# Maps RPM package names to their corresponding flatpak-preinstall package names.
# The preinstall package triggers `flatpak preinstall` via RPM scriptlets on the
# target system, pulling in the Flatpak from the configured remote.
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


def _has_active_subscription():
    """Return True if RHSM is skipped (e.g. Satellite) or the system is registered."""
    if skip_rhsm():
        return True
    rhsm_info = next(api.consume(RHSMInfo), None)
    if not rhsm_info or not rhsm_info.is_registered:
        api.current_logger().warning(
            'System does not have an active Red Hat subscription; '
            'skipping RPM-to-Flatpak migration.'
        )
        return False
    return True


def process():
    if not _has_active_subscription():
        api.produce(RpmToFlatpakFacts())
        return
    packages = _get_packages_to_migrate()
    api.produce(RpmToFlatpakFacts(packages=packages))
