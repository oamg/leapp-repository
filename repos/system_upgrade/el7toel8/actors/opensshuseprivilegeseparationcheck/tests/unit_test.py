import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.models import OpenSshConfig, OpenSshPermitRootLogin, Report
from leapp.snactor.fixture import current_actor_context


def test_no_config(current_actor_context):
    # with pytest.raises(StopActorExecutionError):
    current_actor_context.run()


@pytest.mark.parametrize('value,expected_report', [
    ('', False),
    ('sandbox', False),
    ('yes', True),
    ('no', True)])
def test_separation(current_actor_context, value, expected_report):
    if value:
        current_actor_context.feed(OpenSshConfig(
            permit_root_login=[OpenSshPermitRootLogin(value='no')],
            use_privilege_separation=value
        ))
    else:
        current_actor_context.feed(OpenSshConfig(
            permit_root_login=[OpenSshPermitRootLogin(value='no')]
        ))
    current_actor_context.run()
    if expected_report:
        assert current_actor_context.consume(Report)
    else:
        assert not current_actor_context.consume(Report)


@pytest.mark.parametrize('values,expected_report', [
    (['sandbox', 'yes'], False),
    (['yes', 'sandbox'], True)])
def test_multiple_configs(current_actor_context, values, expected_report):
    for value in values:
        current_actor_context.feed(OpenSshConfig(
            permit_root_login=[OpenSshPermitRootLogin(value='no')],
            use_privilege_separation=value
        ))
    current_actor_context.run()
    if expected_report:
        assert current_actor_context.consume(Report)
    else:
        assert not current_actor_context.consume(Report)
