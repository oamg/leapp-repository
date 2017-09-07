from leapp.models import CheckResult, OSReleaseFacts
from leapp.snactor.fixture import current_actor_context


def test_not_supported_id(current_actor_context):
    current_actor_context.feed(OSReleaseFacts(id='not_supported_id'))
    current_actor_context.run()
    assert current_actor_context.consume(CheckResult)
    assert current_actor_context.consume(CheckResult)[0].summary == 'Unsupported OS id'


def test_not_supported_major_version(current_actor_context):
    current_actor_context.feed(OSReleaseFacts(id='rhel', version_id='6.6'))
    current_actor_context.run()
    assert current_actor_context.consume(CheckResult)
    assert current_actor_context.consume(CheckResult)[0].summary == 'Unsupported OS version'


def test_not_supported_minor_version(current_actor_context):
    current_actor_context.feed(OSReleaseFacts(id='rhel', version_id='7.5'))
    current_actor_context.run()
    assert current_actor_context.consume(CheckResult)
    assert current_actor_context.consume(CheckResult)[0].summary == 'Unsupported OS version'


def test_supported_major_version(current_actor_context):
    current_actor_context.feed(OSReleaseFacts(id='rhel', version_id='8.5'))
    current_actor_context.run()
    assert not current_actor_context.consume(CheckResult)


def test_supported_minor_version(current_actor_context):
    current_actor_context.feed(OSReleaseFacts(id='rhel', version_id='7.7'))
    current_actor_context.run()
    assert not current_actor_context.consume(CheckResult)


def test_same_supported_release(current_actor_context):
    current_actor_context.feed(OSReleaseFacts(id='rhel', version_id='7.6'))
    current_actor_context.run()
    assert not current_actor_context.consume(CheckResult)
