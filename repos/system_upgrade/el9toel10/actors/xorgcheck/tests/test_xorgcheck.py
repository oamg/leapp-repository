import pytest

from leapp import reporting
from leapp.libraries.actor.xorgcheck import report_installed_packages, _XORG_PACKAGES
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, RPM


def _generate_rpm_with_name(name):
    """
    Generate new RPM model item with given name.

    :param name: rpm name
    :type name: str
    :return: new RPM object with name parameter set
    :rtype: RPM
    """
    return RPM(name=name,
               version='0.1',
               release='1.sm01',
               epoch='1',
               pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51',
               packager='Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>',
               arch='noarch')


@pytest.mark.parametrize('xorg_packages', [
    [],  # no Xorg packages
    ['xorg-x11-server-Xorg'],  # single Xorg package
    ['xorg-x11-server-Xorg', 'xorg-x11-server-Xvfb'],  # multiple Xorg packages
    ['xorg-x11-server-Xdmx', 'xorg-x11-server-Xephyr', 'xorg-x11-server-Xnest'],  # other Xorg packages
    _XORG_PACKAGES,  # all Xorg packages
])
def test_actor_execution(monkeypatch, xorg_packages):
    """
    Parametrized helper function for test_actor_* functions.

    First generate list of RPM models based on set arguments. Then, run
    the actor fed with our RPM list. Finally, assert Reports
    according to set arguments.

    Parameters:
        xorg_packages  (list): List of Xorg package names to include
    """

    # Couple of random packages
    rpms = [_generate_rpm_with_name('sed'),
            _generate_rpm_with_name('htop')]

    # Add Xorg packages
    for pkg in xorg_packages:
        rpms.append(_generate_rpm_with_name(pkg))

    curr_actor_mocked = CurrentActorMocked(msgs=[DistributionSignedRPM(items=rpms)])
    monkeypatch.setattr(api, 'current_actor', curr_actor_mocked)
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())

    # Executed actor fed with our fake RPMs
    report_installed_packages()

    if xorg_packages:
        # Assert for Xorg packages installed
        assert reporting.create_report.called == 1
        report_fields = reporting.create_report.report_fields
        resources = report_fields['detail']['related_resources']
        titles = [res['title'] for res in resources]
        assert titles == xorg_packages
        assert all(res['scheme'] == 'package' for res in resources)
    else:
        # Assert for no Xorg packages installed
        assert not reporting.create_report.called
