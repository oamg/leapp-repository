import pytest

from leapp.libraries.actor import migraterpmtoflatpak
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import FlatpakMigrationPackage, RpmToFlatpakFacts


def _make_facts(*rpm_names):
    packages = [
        FlatpakMigrationPackage(
            rpm_name=name,
            preinstall_pkg='redhat-flatpak-preinstall-{}'.format(name),
        )
        for name in rpm_names
    ]
    return RpmToFlatpakFacts(packages=packages)


@pytest.mark.parametrize('facts', [None, _make_facts()])
def test_does_not_run_commands_when_no_packages(monkeypatch, facts):
    msgs = [facts] if facts is not None else []
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    run_calls = []
    monkeypatch.setattr(migraterpmtoflatpak, 'run', lambda cmd, **kw: run_calls.append(cmd))

    migraterpmtoflatpak.process()

    assert not run_calls


def test_runs_flatpak_preinstall_when_packages_present(monkeypatch):
    facts = _make_facts('firefox', 'thunderbird')
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[facts]))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    run_calls = []
    monkeypatch.setattr(migraterpmtoflatpak, 'run', lambda cmd, **kw: run_calls.append(cmd))

    migraterpmtoflatpak.process()

    assert len(run_calls) == 1
    assert run_calls[0] == ['flatpak', 'preinstall', '--system', '--noninteractive']


def test_run_flatpak_preinstall_uses_correct_command(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    run_calls = []
    monkeypatch.setattr(migraterpmtoflatpak, 'run', lambda cmd, **kw: run_calls.append(cmd))

    result = migraterpmtoflatpak._run_flatpak_preinstall()

    assert result is True
    assert run_calls == [['flatpak', 'preinstall', '--system', '--noninteractive']]


def test_run_flatpak_preinstall_logs_error_on_failure(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(migraterpmtoflatpak, 'run', _run_error)

    result = migraterpmtoflatpak._run_flatpak_preinstall()

    assert result is False
    assert api.current_logger.errmsg


def _run_error(cmd, **kwargs):
    raise CalledProcessError(
        message='A Leapp Command Error occurred.',
        command=cmd,
        result={'exit_code': 1},
    )
