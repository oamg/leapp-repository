import pytest

from leapp.libraries.actor import scanrpmtoflatpak
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, RHSMInfo, RPM, RpmToFlatpakFacts


def _make_rpm(name):
    return RPM(name=name, version='1.0', release='1.el9', epoch='0',
               packager='Red Hat', arch='x86_64', pgpsig='SIG')


def _make_rhsm_info(is_registered=True):
    return RHSMInfo(is_registered=is_registered)


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
def test_process_registered(monkeypatch, installed, expected_pkgs):
    msgs = [
        DistributionSignedRPM(items=[_make_rpm(n) for n in installed]),
        _make_rhsm_info(is_registered=True),
    ]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(scanrpmtoflatpak, 'skip_rhsm', lambda: False)

    scanrpmtoflatpak.process()

    assert api.produce.called == 1
    facts = api.produce.model_instances[0]
    assert isinstance(facts, RpmToFlatpakFacts)
    assert len(facts.packages) == len(expected_pkgs)
    result_pairs = sorted((p.rpm_name, p.preinstall_pkg) for p in facts.packages)
    assert result_pairs == sorted(expected_pkgs)


def test_process_not_registered_skips_migration(monkeypatch):
    msgs = [
        DistributionSignedRPM(items=[_make_rpm('firefox')]),
        _make_rhsm_info(is_registered=False),
    ]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(scanrpmtoflatpak, 'skip_rhsm', lambda: False)

    scanrpmtoflatpak.process()

    assert api.produce.called == 1
    facts = api.produce.model_instances[0]
    assert facts.packages == []
    assert any('subscription' in msg.lower() for msg in api.current_logger.warnmsg)


def test_process_no_rhsm_info_skips_migration(monkeypatch):
    msgs = [DistributionSignedRPM(items=[_make_rpm('firefox')])]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(scanrpmtoflatpak, 'skip_rhsm', lambda: False)

    scanrpmtoflatpak.process()

    assert api.produce.called == 1
    assert api.produce.model_instances[0].packages == []


def test_process_skip_rhsm_bypasses_subscription_check(monkeypatch):
    # LEAPP_NO_RHSM=1 means content comes from Satellite — no subscription needed.
    msgs = [DistributionSignedRPM(items=[_make_rpm('firefox')])]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(scanrpmtoflatpak, 'skip_rhsm', lambda: True)

    scanrpmtoflatpak.process()

    assert api.produce.called == 1
    facts = api.produce.model_instances[0]
    assert len(facts.packages) == 1
    assert facts.packages[0].rpm_name == 'firefox'


def test_get_packages_to_migrate_debug_logged(monkeypatch):
    msgs = [DistributionSignedRPM(items=[_make_rpm('firefox')])]
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    packages = scanrpmtoflatpak._get_packages_to_migrate()

    assert len(packages) == 1
    assert packages[0].rpm_name == 'firefox'
    assert any('firefox' in msg for msg in api.current_logger.dbgmsg)
