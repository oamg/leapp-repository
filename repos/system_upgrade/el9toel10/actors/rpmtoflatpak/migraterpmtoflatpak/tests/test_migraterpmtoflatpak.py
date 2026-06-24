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


def _run_error(cmd, **kwargs):
    raise CalledProcessError(
        message='A Leapp Command Error occurred.',
        command=cmd,
        result={'exit_code': 1},
    )


@pytest.mark.parametrize('facts', [None, _make_facts()])
def test_process_no_packages(monkeypatch, facts):
    msgs = [facts] if facts is not None else []
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    run_calls = []
    monkeypatch.setattr(migraterpmtoflatpak, 'run', lambda cmd, **kw: run_calls.append(cmd))

    migraterpmtoflatpak.process()

    assert not run_calls


def test_process_installs_and_preinstalls(monkeypatch):
    facts = _make_facts('firefox', 'thunderbird')
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[facts]))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    run_calls = []
    monkeypatch.setattr(migraterpmtoflatpak, 'run', lambda cmd, **kw: run_calls.append(cmd))

    migraterpmtoflatpak.process()

    assert len(run_calls) == 2
    dnf_cmd = run_calls[0]
    assert dnf_cmd[:3] == ['dnf', 'install', '-y']
    assert 'redhat-flatpak-preinstall-firefox' in dnf_cmd
    assert 'redhat-flatpak-preinstall-thunderbird' in dnf_cmd

    flatpak_cmd = run_calls[1]
    assert flatpak_cmd == ['flatpak', 'preinstall', '--system', '--noninteractive']


def test_process_skips_flatpak_preinstall_on_dnf_failure(monkeypatch):
    facts = _make_facts('firefox')
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[facts]))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    call_count = [0]

    def run_mocked(cmd, **kwargs):
        call_count[0] += 1
        if cmd[:2] == ['dnf', 'install']:
            raise CalledProcessError(
                message='install failed', command=cmd, result={'exit_code': 1}
            )

    monkeypatch.setattr(migraterpmtoflatpak, 'run', run_mocked)

    migraterpmtoflatpak.process()

    assert call_count[0] == 1
    assert any('Failed to install' in msg for msg in api.current_logger.errmsg)


def test_install_preinstall_packages_success(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    run_calls = []
    monkeypatch.setattr(migraterpmtoflatpak, 'run', lambda cmd, **kw: run_calls.append(cmd))

    result = migraterpmtoflatpak._install_preinstall_packages(
        ['redhat-flatpak-preinstall-firefox']
    )

    assert result is True
    assert run_calls == [['dnf', 'install', '-y', 'redhat-flatpak-preinstall-firefox']]


def test_install_preinstall_packages_failure(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(migraterpmtoflatpak, 'run', _run_error)

    result = migraterpmtoflatpak._install_preinstall_packages(
        ['redhat-flatpak-preinstall-firefox']
    )

    assert result is False
    assert api.current_logger.errmsg


def test_run_flatpak_preinstall_success(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    run_calls = []
    monkeypatch.setattr(migraterpmtoflatpak, 'run', lambda cmd, **kw: run_calls.append(cmd))

    result = migraterpmtoflatpak._run_flatpak_preinstall()

    assert result is True
    assert run_calls == [['flatpak', 'preinstall', '--system', '--noninteractive']]


def test_run_flatpak_preinstall_failure(monkeypatch):
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(migraterpmtoflatpak, 'run', _run_error)

    result = migraterpmtoflatpak._run_flatpak_preinstall()

    assert result is False
    assert api.current_logger.errmsg
