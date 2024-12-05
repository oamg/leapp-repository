import pytest
import os

from leapp import reporting
from leapp.libraries.common.testutils import produce_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.libraries import stdlib
from leapp.models import DistributionSignedRPM, RPM

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from repos.system_upgrade.el9toel10.models.mysql import MySQLConfiguration
    from repos.system_upgrade.el9toel10.actors.mysql.scanmysql.libraries import scanmysql
else:
    from leapp.models import MySQLConfiguration
    from leapp.libraries.actor import scanmysql


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


def _run_mocked_valid(args=None, split=None, callback_raw=None,
                      callback_linebuffered=None, env=None, checked=None,
                      stdin=None, encoding=None):
    return {'stderr': ''}


def _run_mocked_invalid(args=None, split=None, callback_raw=None,
                        callback_linebuffered=None, env=None, checked=None,
                        stdin=None, encoding=None):
    return {'stderr':  '2025-01-23T15:28:05.352420Z 0 [Warning] [MY-011069] [Server] The \
                        syntax \'--old\' is deprecated and will be removed in a future release.\n \
                        2025-01-23T15:28:05.352425Z 0 [Warning] [MY-011069] [Server] The \
                        syntax \'avoid_temporal_upgrade\' is deprecated and will be removed \
                        in a future release.'}


@pytest.mark.parametrize('has_server', [
    (True),  # with server
    (False),  # without server
])
def test_server_detection(monkeypatch, has_server):
    """
    Parametrized helper function for test_actor_* functions.

    First generate list of RPM models based on set arguments. Then, run
    the actor fed with our RPM list. Finally, assert Reports
    according to set arguments.

    Parameters:
        has_server  (bool): mysql-server installed
    """

    # Couple of random packages
    rpms = [_generate_rpm_with_name('sed'),
            _generate_rpm_with_name('htop')]

    if has_server:
        # Add mysql-server
        rpms += [_generate_rpm_with_name('mysql-server')]

    curr_actor_mocked = CurrentActorMocked(msgs=[DistributionSignedRPM(items=rpms)])
    monkeypatch.setattr(api, 'current_actor', curr_actor_mocked)
    monkeypatch.setattr(api, 'produce', produce_mocked)
    monkeypatch.setattr(scanmysql, 'run', _run_mocked_valid)

    result: MySQLConfiguration = scanmysql.check_status()

    assert result.mysql_present == has_server


@pytest.mark.parametrize('valid_conf', [True, False])
@pytest.mark.parametrize('valid_args', [True, False])
def test_configuration_check(monkeypatch, valid_conf, valid_args):
    """
    Parametrized helper function for test_actor_* functions.

    First generate list of RPM models based on set arguments. Then, run
    the actor fed with our RPM list. Finally, assert Reports
    according to set arguments.

    Parameters:
        has_server  (bool): mysql-server installed
    """

    # Couple of random packages
    rpms = [_generate_rpm_with_name('sed'),
            _generate_rpm_with_name('htop'),
            _generate_rpm_with_name('mysql-server')]

    curr_actor_mocked = CurrentActorMocked(msgs=[DistributionSignedRPM(items=rpms)])
    monkeypatch.setattr(api, 'current_actor', curr_actor_mocked)
    monkeypatch.setattr(api, 'produce', produce_mocked)

    if valid_conf:
        monkeypatch.setattr(scanmysql, 'run', _run_mocked_valid)
    else:
        monkeypatch.setattr(scanmysql, 'run', _run_mocked_invalid)

    if not valid_args:
        monkeypatch.setattr(scanmysql, 'SERVICE_OVERRIDE_PATH',
                            os.path.dirname(os.path.realpath(__file__))+'/service_invalid.txt')

    result: MySQLConfiguration = scanmysql.check_status()

    if valid_conf:
        assert len(result.removed_options) == 0
    else:
        assert len(result.removed_options) == 2

    if valid_args:
        assert len(result.removed_arguments) == 0
    else:
        assert len(result.removed_arguments) == 1
