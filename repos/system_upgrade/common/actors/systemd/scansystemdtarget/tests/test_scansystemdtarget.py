import pytest

from leapp.libraries.actor import scansystemdtarget
from leapp.libraries.common import systemd
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import (
    SystemdBrokenSymlinksTarget,
    SystemdServiceFile,
    SystemdServicePreset,
    SystemdServicesInfoTarget,
    SystemdServicesPresetInfoTarget
)

_BROKEN_SYMLINKS = [
    "/etc/systemd/system/multi-user.target.wants/vdo.service",
    "/etc/systemd/system/multi-user.target.wants/rngd.service"
]

_SERVICE_FILES = [
    SystemdServiceFile(name='getty@.service', state='enabled'),
    SystemdServiceFile(name='vdo.service', state='disabled')
]

_PRESETS = [
    SystemdServicePreset(service='getty@.service', state='enable'),
    SystemdServicePreset(service='vdo.service', state='disable'),
]


@pytest.mark.parametrize(
    ('broken_symlinks', 'files', 'presets'),
    (
        (_BROKEN_SYMLINKS, _SERVICE_FILES, _PRESETS),
        ([], [], [])
    )
)
def test_message_produced(monkeypatch, broken_symlinks, files, presets):

    def scan_broken_symlinks_mocked():
        return broken_symlinks

    def get_service_files_mocked():
        return files

    def get_system_service_preset_files_mocked(service_files, ignore_invalid_entries):
        return presets

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(systemd, 'get_broken_symlinks', scan_broken_symlinks_mocked)
    monkeypatch.setattr(systemd, 'get_service_files', get_service_files_mocked)
    monkeypatch.setattr(systemd, 'get_system_service_preset_files', get_system_service_preset_files_mocked)

    scansystemdtarget.scan()

    assert api.produce.called
    assert api.produce.model_instances[0].broken_symlinks == broken_symlinks
    assert api.produce.model_instances[1].service_files == files
    assert api.produce.model_instances[2].presets == presets


_CALL_PROC_ERR = CalledProcessError(
    message='BooCalled',
    command=['find'],
    result={
        'stdout': 'stdout',
        'stderr': 'stderr',
        'exit_code': 1,
        'signal': 1,
        'pid': 1,
    }
)


class GetOrRaise(object):
    def __init__(self, value):
        self.value = value

    def __call__(self, *dummyArgs, **dummy):
        if isinstance(self.value, list):
            return self.value
        raise self.value


@pytest.mark.parametrize('symlinks', [OSError('Boo'), _CALL_PROC_ERR, []])
@pytest.mark.parametrize('files', [_CALL_PROC_ERR, []])
@pytest.mark.parametrize('presets', [OSError('Boo'), _CALL_PROC_ERR, []])
def test_exception_handling(monkeypatch, symlinks, files, presets):

    def check_msg(input_data, msg_type, msgs, is_msg_expected):
        for msg in msgs.model_instances:
            if isinstance(msg, msg_type):
                return is_msg_expected
        return not is_msg_expected

    if symlinks == files == presets == []:
        # covered by test above
        return

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(systemd, 'get_broken_symlinks', GetOrRaise(symlinks))
    monkeypatch.setattr(systemd, 'get_service_files', GetOrRaise(files))
    monkeypatch.setattr(systemd, 'get_system_service_preset_files', GetOrRaise(presets))
    scansystemdtarget.scan()
    assert check_msg(symlinks, SystemdBrokenSymlinksTarget, api.produce, isinstance(symlinks, list))
    assert check_msg(files, SystemdServicesInfoTarget, api.produce, isinstance(files, list))
    is_msg_expected = isinstance(files, list) and isinstance(presets, list)
    assert check_msg(presets, SystemdServicesPresetInfoTarget, api.produce, is_msg_expected)
