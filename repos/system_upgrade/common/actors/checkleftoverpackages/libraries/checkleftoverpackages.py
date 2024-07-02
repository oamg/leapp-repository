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

    to_remove = LeftoverPackages()
    unsigned = [pkg.name for pkg in next(api.consume(InstalledUnsignedRPM), InstalledUnsignedRPM()).items]

    for rpm in installed_rpms:
        rpm = rpm.strip()
        if not rpm:
            continue
        name, version, release, epoch, packager, arch, pgpsig = rpm.split('|')

        version_pattern = r'el(\d+)'
        match = re.search(version_pattern, release)

        if match:
            major_version = match.group(1)
            PKGS_NOT_TO_BE_DELETED = set(LEAPP_PACKAGES + LEAPP_DEP_PACKAGES + unsigned)
            if int(major_version) <= int(get_source_major_version()) and name not in PKGS_NOT_TO_BE_DELETED:
                to_remove.items.append(RPM(
                    name=name,
                    version=version,
                    epoch=epoch,
                    packager=packager,
                    arch=arch,
                    release=release,
                    pgpsig=pgpsig
                ))

    api.produce(to_remove)
