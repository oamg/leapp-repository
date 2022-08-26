from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import systemd
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import SystemdBrokenSymlinksSource, SystemdServicesInfoSource, SystemdServicesPresetInfoSource


def scan():
    try:
        broken_symlinks = systemd.get_broken_symlinks()
    except (OSError, CalledProcessError) as err:
        details = {'details': str(err)}
        if isinstance(err, CalledProcessError):
            details['stderr'] = err.stderr
        raise StopActorExecutionError(
            message='Cannot scan the system to list possible broken systemd symlinks.',
            details=details
        )

    try:
        services_files = systemd.get_service_files()
    except CalledProcessError as err:
        raise StopActorExecutionError(
            message='Cannot obtain the list of systemd service unit files.',
            details={'details': str(err), 'stderr': err.stderr}
        )

    try:
        presets = systemd.get_system_service_preset_files(services_files, ignore_invalid_entries=False)
    except (OSError, CalledProcessError) as err:
        details = {'details': str(err)}
        if isinstance(err, CalledProcessError):
            details['stderr'] = err.stderr
        raise StopActorExecutionError(
            message='Cannot obtain the list of systemd preset files.',
            details=details
        )
    except ValueError as err:
        raise StopActorExecutionError(
            message='Discovered an invalid systemd preset file.',
            details={'details': str(err)}
        )

    api.produce(SystemdBrokenSymlinksSource(broken_symlinks=broken_symlinks))
    api.produce(SystemdServicesInfoSource(service_files=services_files))
    api.produce(SystemdServicesPresetInfoSource(presets=presets))
