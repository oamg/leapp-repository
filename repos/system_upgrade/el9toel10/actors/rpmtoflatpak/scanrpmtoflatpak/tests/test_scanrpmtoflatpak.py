import pytest

from leapp.libraries.actor import scanrpmtoflatpak
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, RPM, RpmToFlatpakFacts


def _make_rpm(name):
    return RPM(name=name, version='1.0', release='1.el9', epoch='0',
               packager='Red Hat', arch='x86_64', pgpsig='SIG')


@pytest.mark.parametrize('installed,expected_pkgs', [
    ([], []),
    (['firefox'], [('firefox', 'redhat-flatpak-preinstall-firefox')]),
    (['thunderbird'], [('thunderbird', 'redhat-flatpak-preinstall-thunderbird')]),
    (
        ['firefox', 'thunderbird'],
        [
            ('firefox', 'redhat-flatpak-preinstall-firefox'),
            ('thunderbird', 'redhat-flatpak-preinstall-thunderbird'),
        ],
    ),
    (['vim-enhanced', 'bash'], []),
])
def test_produces_migration_facts_for_installed_flatpak_rpms(monkeypatch, installed, expected_pkgs):
    msgs = [DistributionSignedRPM(items=[_make_rpm(n) for n in installed])]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(api, 'produce', produce_mocked())

    scanrpmtoflatpak.process()

    assert api.produce.called == 1
    facts = api.produce.model_instances[0]
    assert isinstance(facts, RpmToFlatpakFacts)
    assert len(facts.packages) == len(expected_pkgs)
    result_pairs = sorted((p.rpm_name, p.preinstall_pkg) for p in facts.packages)
    assert result_pairs == sorted(expected_pkgs)


def test_logs_debug_for_each_detected_package(monkeypatch):
    msgs = [DistributionSignedRPM(items=[_make_rpm('firefox')])]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    packages = scanrpmtoflatpak._get_packages_to_migrate()

    assert len(packages) == 1
    assert packages[0].rpm_name == 'firefox'
    assert any('firefox' in msg for msg in api.current_logger.dbgmsg)
