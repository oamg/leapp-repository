import pytest

from leapp import reporting
from leapp.libraries.actor.mariadbcheck import report_installed_packages
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import InstalledRedHatSignedRPM, RPM


def _generate_rpm_with_name(name):
    """
    Generate new RPM model item with given name.

    Parameters:
        name (str): rpm name

    Returns:
        rpm  (RPM): new RPM object with name parameter set
    """
    return RPM(name=name,
               version='0.1',
               release='1.sm01',
               epoch='1',
               pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51',
               packager='Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>',
               arch='noarch')


@pytest.mark.parametrize('has_server', [
    (True),  # with server
    (False),  # without server
])
def test_actor_execution(monkeypatch, has_server):
    """
    Parametrized helper function for test_actor_* functions.

    First generate list of RPM models based on set arguments. Then, run
    the actor fed with our RPM list. Finally, assert Reports
    according to set arguments.

    Parameters:
        has_server  (bool): mariadb-server installed
    """

    # Couple of random packages
    rpms = [_generate_rpm_with_name('sed'),
            _generate_rpm_with_name('htop')]

    if has_server:
        # Add mariadb-server
        rpms += [_generate_rpm_with_name('mariadb-server')]

    curr_actor_mocked = CurrentActorMocked(msgs=[InstalledRedHatSignedRPM(items=rpms)])
    monkeypatch.setattr(api, 'current_actor', curr_actor_mocked)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    # Executed actor fed with fake RPMs
    report_installed_packages(_context=api)

    if has_server:
        # Assert for mariadb-server package installed
        assert reporting.create_report.called == 1
    else:
        # Assert for no mariadb packages installed
        assert not reporting.create_report.called
