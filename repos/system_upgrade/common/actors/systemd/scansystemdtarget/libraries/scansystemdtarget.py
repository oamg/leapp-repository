from leapp.libraries.common import systemd
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import SystemdBrokenSymlinksTarget, SystemdServicesInfoTarget, SystemdServicesPresetInfoTarget


def scan_broken_symlinks():
    try:
        broken_symlinks = systemd.get_broken_symlinks()
    except (OSError, CalledProcessError):
        return
    api.produce(SystemdBrokenSymlinksTarget(broken_symlinks=broken_symlinks))


def scan_service_files():
    try:
        services_files = systemd.get_service_files()
    except CalledProcessError:
        return None
    api.produce(SystemdServicesInfoTarget(service_files=services_files))
    return services_files


def scan_preset_files(services_files):
    if services_files is None:
        return
    try:
        presets = systemd.get_system_service_preset_files(services_files, ignore_invalid_entries=True)
    except (OSError, CalledProcessError):
        return
    api.produce(SystemdServicesPresetInfoTarget(presets=presets))


def scan():
    # Errors are logged inside the systemd library, no need to log them here again.
    scan_broken_symlinks()
    services_files = scan_service_files()
    scan_preset_files(services_files)
