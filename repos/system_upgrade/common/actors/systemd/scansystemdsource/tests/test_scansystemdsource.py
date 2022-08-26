import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import scansystemdsource
from leapp.libraries.common import systemd
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import (
    SystemdServiceFile,
    SystemdServicePreset,
    SystemdServicesInfoSource,
    SystemdServicesPresetInfoSource
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

    def get_broken_symlinks_mocked():
        return broken_symlinks

    def get_service_files_mocked():
        return files

    def get_system_service_preset_files_mocked(service_files, ignore_invalid_entries):
        return presets

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(systemd, 'get_broken_symlinks', get_broken_symlinks_mocked)
    monkeypatch.setattr(systemd, 'get_service_files', get_service_files_mocked)
    monkeypatch.setattr(systemd, 'get_system_service_preset_files', get_system_service_preset_files_mocked)

    scansystemdsource.scan()

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
@pytest.mark.parametrize('presets', [OSError('Boo'), _CALL_PROC_ERR, ValueError('Hamster'), []])
def test_exception_handling(monkeypatch, symlinks, files, presets):
    if symlinks == files == presets == []:
        # covered by test above
        return

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(systemd, 'get_broken_symlinks', GetOrRaise(symlinks))
    monkeypatch.setattr(systemd, 'get_service_files', GetOrRaise(files))
    monkeypatch.setattr(systemd, 'get_system_service_preset_files', GetOrRaise(presets))
    with pytest.raises(StopActorExecutionError):
        scansystemdsource.scan()
