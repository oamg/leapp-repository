import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import opensshalgorithmscheck
from leapp.models import OpenSshConfig, OpenSshPermitRootLogin, Report
from leapp.snactor.fixture import current_actor_context


def test_no_config(current_actor_context):
    with pytest.raises(StopActorExecutionError):
        opensshalgorithmscheck.process(iter([]))


osprl = OpenSshPermitRootLogin(value='no')


@pytest.mark.parametrize('ciphers,expected_report', [
    (None, False),
    ('aes128-ctr', False),
    ('aes128-ctr,aes192-ctr,aes256-ctr', False),
    ('arcfour', True),
    ('arcfour,arcfour128,arcfour256', True),
    ('arcfour,aes128-ctr', True),
    ('aes128-ctr,arcfour', True)])
def test_ciphers(current_actor_context, ciphers, expected_report):
    current_actor_context.feed(OpenSshConfig(
        permit_root_login=[osprl],
        ciphers=ciphers
    ))
    current_actor_context.run()
    if expected_report:
        assert current_actor_context.consume(Report)
    else:
        assert not current_actor_context.consume(Report)
