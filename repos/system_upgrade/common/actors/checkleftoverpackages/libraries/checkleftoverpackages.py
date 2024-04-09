import re

from leapp.libraries.common.config.version import get_source_major_version
from leapp.libraries.common.rpms import get_installed_rpms, get_leapp_dep_packages, get_leapp_packages
from leapp.libraries.stdlib import api
from leapp.models import InstalledUnsignedRPM, LeftoverPackages, RPM


def process():
    LEAPP_PACKAGES = get_leapp_packages(major_version=[get_source_major_version()])
    LEAPP_DEP_PACKAGES = get_leapp_dep_packages(major_version=[get_source_major_version()])
    installed_rpms = get_installed_rpms()

    if not installed_rpms:
        return

    leftover_pkgs_to_remove = []
    unsigned = [pkg.name for pkg in next(api.consume(InstalledUnsignedRPM), InstalledUnsignedRPM()).items]

    for rpm in installed_rpms:
        rpm = rpm.strip()
        if not rpm:
            continue
        try:
            name, version, release, epoch, packager, arch, pgpsig = rpm.split('|')
        except ValueError:
            api.current_logger().warning('Could not parse rpm: {}, skipping'.format(rpm))
            continue

        version_pattern = r'el(\d+)'
        match = re.search(version_pattern, release)

        if match:
            major_version = match.group(1)
            PKGS_NOT_TO_BE_DELETED = set(LEAPP_PACKAGES + LEAPP_DEP_PACKAGES + unsigned)
            if int(major_version) <= int(get_source_major_version()) and name not in PKGS_NOT_TO_BE_DELETED:
                leftover_pkgs_to_remove.append(RPM(
                    name=name,
                    version=version,
                    epoch=epoch,
                    packager=packager,
                    arch=arch,
                    release=release,
                    pgpsig=pgpsig
                ))

    api.produce(LeftoverPackages(items=leftover_pkgs_to_remove))
