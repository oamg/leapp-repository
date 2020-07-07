import pytest

from leapp.snactor.fixture import current_actor_context
from leapp.models import (
    InstalledRedHatSignedRPM,
    InstalledRPM,
    RPM,
    RHUIInfo,
    RequiredTargetUserspacePackages,
)
from leapp.reporting import Report
from leapp.libraries.common.config import mock_configs
from leapp.libraries.common import rhsm


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


def test_actor_no_rhui(current_actor_context):
    current_actor_context.feed(create_modulesfacts(installed_rpm=NO_RHUI))
    current_actor_context.run(config_model=mock_configs.CONFIG)
    assert not current_actor_context.consume(Report)
    assert not current_actor_context.consume(RHUIInfo)
    assert not current_actor_context.consume(RequiredTargetUserspacePackages)


def test_actor_rhui_without_leapp_package(monkeypatch, current_actor_context):
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: True)

    current_actor_context.feed(create_modulesfacts(installed_rpm=ON_AWS_WITHOUT_LEAPP_PKG))
    current_actor_context.run(config_model=mock_configs.CONFIG)
    assert current_actor_context.consume(Report)
    assert not current_actor_context.consume(RHUIInfo)
    assert not current_actor_context.consume(RequiredTargetUserspacePackages)


def test_actor_rhui_with_leapp_package(monkeypatch, current_actor_context):
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: True)

    current_actor_context.feed(create_modulesfacts(installed_rpm=ON_AWS_WITH_LEAPP_PKG))
    current_actor_context.run(config_model=mock_configs.CONFIG)
    assert not current_actor_context.consume(Report)
    assert current_actor_context.consume(RHUIInfo)
    assert current_actor_context.consume(RequiredTargetUserspacePackages)


def test_actor_without_no_rhsm(monkeypatch, current_actor_context):
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: False)
    
    current_actor_context.feed(create_modulesfacts(installed_rpm=ON_AWS_WITH_LEAPP_PKG))
    current_actor_context.run(config_model=mock_configs.CONFIG)
    assert current_actor_context.consume(Report)
    assert not current_actor_context.consume(RHUIInfo)
    assert not current_actor_context.consume(RequiredTargetUserspacePackages)
