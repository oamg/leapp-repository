import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import opensshprotocolcheck
from leapp.models import OpenSshConfig, OpenSshPermitRootLogin, Report
from leapp.snactor.fixture import current_actor_context


def test_no_config(current_actor_context):
    with pytest.raises(StopActorExecutionError):
        opensshprotocolcheck.process(iter([]))


osprl = OpenSshPermitRootLogin(value='no')


@pytest.mark.parametrize('protocol', [None, '1', '2', '1,2', '2,1', '7'])
def test_protocol(current_actor_context, protocol):
    current_actor_context.feed(OpenSshConfig(
        permit_root_login=[osprl],
        protocol=protocol
    ))
    current_actor_context.run()
    if protocol:
        assert current_actor_context.consume(Report)
    else:
        assert not current_actor_context.consume(Report)
