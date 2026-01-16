import pytest

from leapp.libraries.actor import checkkernelrt
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, RPM


def _rpm(name):
    return RPM(
        name=name,
        arch='x86_64',
        version='1',
        release='1',
        epoch='0',
        packager='Red Hat',
        pgpsig='SOME_SIG'
    )


@pytest.mark.parametrize(
    ('pkgs', 'expect_produce'),
    [
        ([], False),
        ([_rpm('kernel')], False),
        ([_rpm('kernel-rt'), _rpm('kernel-rt-core'), _rpm('kernel-rt-modules'), _rpm('kernel')], True),
    ]
)
def test_kernel_rt_workaround(monkeypatch, pkgs, expect_produce):
    current_actor_mocked = CurrentActorMocked(msgs=[DistributionSignedRPM(items=pkgs)])
    monkeypatch.setattr(api, "current_actor", current_actor_mocked)
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkkernelrt.process()

    if expect_produce:
        assert api.produce.called == 1
        rpm_tasks = api.produce.model_instances[0]
        assert rpm_tasks.to_remove == ['kernel-rt']
        assert rpm_tasks.to_upgrade == ['kernel-rt-core']
    else:
        assert not api.produce.called
