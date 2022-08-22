from collections import namedtuple

import pytest

from leapp.libraries.common import rhsm
from leapp.libraries.common.config import mock_configs
from leapp.models import (
    InstalledRedHatSignedRPM,
    InstalledRPM,
    RequiredTargetUserspacePackages,
    RHUIInfo,
    RPM
)
from leapp.reporting import Report
from leapp.snactor.fixture import current_actor_context

RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'

NO_RHUI = [
    RPM(name='yolo', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
        pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51'),
]

ON_AWS_WITHOUT_LEAPP_PKG = [
    RPM(name='rh-amazon-rhui-client', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER,
        arch='noarch', pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51'),
]

ON_AWS_WITH_LEAPP_PKG = [
    RPM(name='rh-amazon-rhui-client', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER,
        arch='noarch', pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51'),
    RPM(name='leapp-rhui-aws', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER,
        arch='noarch', pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51')
]


def create_modulesfacts(installed_rpm):
    return InstalledRPM(items=installed_rpm)


msgs_received = namedtuple('MsgsReceived', ['report', 'rhui_info', 'req_target_userspace'])


@pytest.mark.parametrize('skip_rhsm, msgs_received, installed_rpms', [
    (False, msgs_received(False, False, False), NO_RHUI),
    (True, msgs_received(True, False, False), ON_AWS_WITHOUT_LEAPP_PKG),
    (True, msgs_received(False, True, True), ON_AWS_WITH_LEAPP_PKG),
    (False, msgs_received(True, False, False), ON_AWS_WITH_LEAPP_PKG)
])
def test_check_rhui_actor(
    monkeypatch, current_actor_context, skip_rhsm, msgs_received, installed_rpms
):
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: skip_rhsm)

    current_actor_context.feed(create_modulesfacts(installed_rpm=installed_rpms))
    current_actor_context.run(config_model=mock_configs.CONFIG)
    assert bool(current_actor_context.consume(Report)) is msgs_received.report
    assert bool(current_actor_context.consume(RHUIInfo)) is msgs_received.rhui_info
    assert bool(current_actor_context.consume(
        RequiredTargetUserspacePackages)) is msgs_received.req_target_userspace
