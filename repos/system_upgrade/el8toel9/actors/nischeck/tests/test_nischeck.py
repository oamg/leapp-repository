import functools

import pytest

from leapp import reporting
from leapp.libraries.actor import nischeck
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import InstalledRedHatSignedRPM, NISConfig, RPM

_generate_rpm = functools.partial(RPM,
                                  pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51',
                                  packager='Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>',
                                  arch='noarch')


@pytest.mark.parametrize('pkgs_installed', [
    ('ypserv',),
    ('ypbind',),
    ('ypserv-not-ypbind',),
    ('ypbind', 'ypserv'),
])
@pytest.mark.parametrize('pkgs_configured', [
    (),
    ('ypbind',),
    ('ypserv',),
    ('ypbind', 'ypserv'),
])
def test_actor_nis(monkeypatch, pkgs_installed, pkgs_configured):
    """
    Parametrized helper function for test_actor_* functions.

    First generate list of RPM models based on set arguments. Then, run
    the actor feeded with our RPM list and mocked functions. Finally, assert
    Reports according to set arguments.

    Parameters:
        pkgs_installed  (touple): installed pkgs
        fill_conf_file  (bool): not default ypbind config file
        fill_ypserv_dir  (bool): not default ypserv dir content
    """

    # Generate few standard packages
    rpms = [_generate_rpm(name='rclone', version='2.3', release='3', epoch='1'),
            _generate_rpm(name='gdb', version='2.0.1', release='1', epoch='2')]

    # Generate packages from 'pkgs_installed'
    for pkg_name in pkgs_installed:
        rpms += [_generate_rpm(name=pkg_name, version='2.0', release='3', epoch='1')]

    # Generate NIS facts
    nis_facts = NISConfig(nis_not_default_conf=pkgs_configured)

    curr_actor_mocked = CurrentActorMocked(msgs=[InstalledRedHatSignedRPM(items=rpms), nis_facts])
    monkeypatch.setattr(api, 'current_actor', curr_actor_mocked)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    # Executed actor feeded with out fake msgs
    nischeck.report_nis()

    # Iterate through installed packages
    for pkg in pkgs_installed:
        # Check if package is configured
        if pkg in pkgs_configured:
            # Don't waste time checking other conditions
            # if one of pkgs is already found
            assert reporting.create_report.called == 1
            break
    else:
        # Assert for no NIS installed and configured packages
        assert not reporting.create_report.called
