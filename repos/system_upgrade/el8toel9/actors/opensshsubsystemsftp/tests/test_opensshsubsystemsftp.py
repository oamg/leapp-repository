import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import opensshsubsystemsftp
from leapp.models import OpenSshConfig, Report


def test_no_config(current_actor_context):
    with pytest.raises(StopActorExecutionError):
        opensshsubsystemsftp.process(iter([]))


@pytest.mark.parametrize('modified,subsystem,expected_report', [
    (False, None, False),  # should not happen
    (False, '/usr/libexec/openssh/sftp-server', False),  # Defaults
    (True, None, True),
    (True, 'internal-sftp', False),
    (True, '/usr/libexec/openssh/sftp-server', False)
])
def test_subsystem(current_actor_context, modified, subsystem, expected_report):
    conf = OpenSshConfig(
        modified=modified,
        permit_root_login=[],
        deprecated_directives=[]
    )
    if subsystem is not None:
        conf.subsystem_sftp = subsystem
    current_actor_context.feed(conf)
    current_actor_context.run()
    if expected_report:
        assert current_actor_context.consume(Report)
    else:
        assert not current_actor_context.consume(Report)
