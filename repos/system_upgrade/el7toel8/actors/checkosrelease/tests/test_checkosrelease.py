from leapp.models import OSReleaseFacts
from leapp.reporting import Report
from leapp.snactor.fixture import current_actor_context


def create_osrelease(release_id, version_id=None):
    version_id = version_id or '42'
    return OSReleaseFacts(
        id=release_id,
        name='test',
        pretty_name='test {}'.format(version_id),
        version='Some Test {}'.format(version_id),
        version_id=version_id,
        variant=None,
        variant_id=None
    )


def test_not_supported_id(current_actor_context):
    current_actor_context.feed(create_osrelease(release_id='not_supported_id'))
    current_actor_context.run()
    assert current_actor_context.consume(Report)
    assert current_actor_context.consume(Report)[0].title == 'Unsupported OS id'
    assert 'inhibitor' in current_actor_context.consume(Report)[0].flags


def test_not_supported_major_version(current_actor_context):
    current_actor_context.feed(create_osrelease(release_id='rhel', version_id='6.6'))
    current_actor_context.run()
    assert current_actor_context.consume(Report)
    assert current_actor_context.consume(Report)[0].title == 'Unsupported OS version'
    assert 'inhibitor' in current_actor_context.consume(Report)[0].flags


def test_not_supported_minor_version(current_actor_context):
    current_actor_context.feed(create_osrelease(release_id='rhel', version_id='7.5'))
    current_actor_context.run()
    assert current_actor_context.consume(Report)
    assert current_actor_context.consume(Report)[0].title == 'Unsupported OS version'
    assert 'inhibitor' in current_actor_context.consume(Report)[0].flags


def test_supported_major_version(current_actor_context):
    current_actor_context.feed(create_osrelease(release_id='rhel', version_id='8.5'))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)


def test_supported_minor_version(current_actor_context):
    current_actor_context.feed(create_osrelease(release_id='rhel', version_id='7.7'))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)


def test_same_supported_release(current_actor_context):
    current_actor_context.feed(create_osrelease(release_id='rhel', version_id='7.6'))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)
