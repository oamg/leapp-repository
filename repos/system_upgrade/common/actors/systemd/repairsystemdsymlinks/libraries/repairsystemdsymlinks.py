import os

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import systemd
from leapp.libraries.common.config.version import get_target_major_version
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import SystemdBrokenSymlinksSource, SystemdBrokenSymlinksTarget, SystemdServicesInfoSource

_INSTALLATION_CHANGED_EL8 = ['rngd.service', 'sysstat.service']
_INSTALLATION_CHANGED_EL9 = []


def _get_installation_changed_units():
    version = get_target_major_version()
    if version == '8':
        return _INSTALLATION_CHANGED_EL8
    if version == '9':
        return _INSTALLATION_CHANGED_EL9

    return []


def _service_enabled_source(service_info, name):
    service_file = next((s for s in service_info.service_files if s.name == name), None)
    return service_file and service_file.state == 'enabled'


def _is_unit_enabled(unit):
    try:
        ret = run(['systemctl', 'is-enabled', unit], split=True)['stdout']
        return ret and ret[0] == 'enabled'
    except (OSError, CalledProcessError):
        return False


def _handle_newly_broken_symlinks(symlinks, service_info):
    for symlink in symlinks:
        unit = os.path.basename(symlink)
        try:
            if not _is_unit_enabled(unit):
                # removes the broken symlink
                systemd.disable_unit(unit)
            elif _service_enabled_source(service_info, unit) and _is_unit_enabled(unit):
                # removes the old symlinks and creates the new ones
                systemd.reenable_unit(unit)
        except CalledProcessError:
            # TODO(mmatuska): Produce post-upgrade report: failed to handle broken symlink (and suggest a fix?)
            pass


def _handle_bad_symlinks(service_files):
    install_changed_units = _get_installation_changed_units()
    potentially_bad = [s for s in service_files if s.name in install_changed_units]

    for unit_file in potentially_bad:
        if unit_file.state == 'enabled' and _is_unit_enabled(unit_file.name):
            systemd.reenable_unit(unit_file.name)


def process():
    service_info_source = next(api.consume(SystemdServicesInfoSource), None)
    if not service_info_source:
        raise StopActorExecutionError("Expected SystemdServicesInfoSource message, but got None")

    source_info = next(api.consume(SystemdBrokenSymlinksSource), None)
    target_info = next(api.consume(SystemdBrokenSymlinksTarget), None)

    if source_info and target_info:
        newly_broken = []
        newly_broken = [s for s in target_info.broken_symlinks if s not in source_info.broken_symlinks]
        if not newly_broken:
            return

        _handle_newly_broken_symlinks(newly_broken, service_info_source)

    _handle_bad_symlinks(service_info_source.service_files)
