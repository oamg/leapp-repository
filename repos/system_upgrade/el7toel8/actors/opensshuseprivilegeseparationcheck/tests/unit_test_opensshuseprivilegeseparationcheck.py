import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import opensshuseprivilegeseparationcheck
from leapp.models import OpenSshConfig, OpenSshPermitRootLogin, Report
from leapp.snactor.fixture import current_actor_context


def test_no_config(current_actor_context):
    with pytest.raises(StopActorExecutionError):
        opensshuseprivilegeseparationcheck.process(iter([]))


osprl = OpenSshPermitRootLogin(value='no')


@pytest.mark.parametrize('values,expected_report', [
    ([''], False),
    (['sandbox'], False),
    (['yes'], True),
    (['no'], True),
    (['sandbox', 'yes'], False),
    (['yes', 'sandbox'], True)])
def test_separation(current_actor_context, values, expected_report):
    for value in values:
        if value:
            current_actor_context.feed(OpenSshConfig(
                permit_root_login=[osprl],
                use_privilege_separation=value
            ))
        else:
            current_actor_context.feed(OpenSshConfig(
                permit_root_login=[osprl]
            ))
    current_actor_context.run()
    if expected_report:
        assert current_actor_context.consume(Report)
    else:
        assert not current_actor_context.consume(Report)
