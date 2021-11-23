import pytest

from leapp import reporting
from leapp.libraries.actor import checkselinux
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import Report, SELinuxFacts, SelinuxPermissiveDecision, SelinuxRelabelDecision
from leapp.snactor.fixture import current_actor_context


def create_selinuxfacts(static_mode, enabled, policy='targeted', mls_enabled=True):
    runtime_mode = static_mode if static_mode != 'disabled' else None

    return SELinuxFacts(
        runtime_mode=runtime_mode,
        static_mode=static_mode,
        enabled=enabled,
        policy=policy,
        mls_enabled=mls_enabled
    )


@pytest.mark.parametrize('mode', ('permissive', 'enforcing'))
def test_actor_schedule_relabelling(monkeypatch, mode):

    fact = create_selinuxfacts(static_mode=mode, enabled=True)

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[fact]))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    checkselinux.process()

    assert api.produce.model_instances[0].set_relabel
    assert reporting.create_report.called


def test_actor_set_permissive(monkeypatch):
    relabel = create_selinuxfacts(static_mode='enforcing', enabled=True)

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[relabel]))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    checkselinux.process()

    assert api.produce.model_instances[0].set_relabel
    assert api.produce.model_instances[1].set_permissive
    assert reporting.create_report.called


@pytest.mark.parametrize('el8_to_el9', (True, False))
def test_actor_selinux_disabled(monkeypatch, el8_to_el9):
    disabled = create_selinuxfacts(enabled=False, static_mode='disabled')

    target_ver = '8' if not el8_to_el9 else '9'

    monkeypatch.setattr(checkselinux, 'get_target_major_version', lambda: target_ver)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[disabled]))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    checkselinux.process()
    if el8_to_el9:
        assert api.produce.model_instances[0]
        assert reporting.create_report.called == 2
    else:
        assert not api.produce.model_instances
        assert reporting.create_report.called
