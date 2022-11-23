from leapp.models import BlackListCA, BlackListError, Report
from leapp.utils.report import is_inhibitor


def test_actor_execution_empty(current_actor_context):
    current_actor_context.feed()
    current_actor_context.run()
    assert not current_actor_context.consume(Report)


def test_actor_error_entry(current_actor_context):
    current_actor_context.feed(
        BlackListError(
            sourceDir="/blacklist",
            targetDir="/blocklist",
            error="Can't list /blacklist"
        )
    )
    current_actor_context.run()
    r = current_actor_context.consume(Report)
    assert r
    assert 'Could not access blacklist directory' in r[0].report['title']
    assert is_inhibitor(r[0].report)


def test_actor_single_entry(current_actor_context):
    current_actor_context.feed(
        BlackListCA(
            source="/blacklist/badcert.ca",
            sourceDir="/blacklist",
            target="/blocklist/badcert.ca",
            targetDir="/blocklist"
        )
    )
    current_actor_context.run()
    r = current_actor_context.consume(Report)
    assert r
    assert ('/blacklist/badcert.ca will be moved to /blocklist and '
            '/blacklist will be deleted') in r[0].report['summary']


def test_actor_two_entries_one_directory(current_actor_context):
    current_actor_context.feed(
        BlackListCA(
            source="/blacklist/badcert.ca",
            sourceDir="/blacklist",
            target="/blocklist/badcert.ca",
            targetDir="/blocklist"
        ),
        BlackListCA(
            source="/blacklist/badcert2.ca",
            sourceDir="/blacklist",
            target="/blocklist/badcert2.ca",
            targetDir="/blocklist"
        ),
    )
    current_actor_context.run()
    r = current_actor_context.consume(Report)
    assert r
    assert ('/blacklist/badcert.ca and /blacklist/badcert2.ca '
            'will be moved to /blocklist and /blacklist will '
            'be deleted') in r[0].report['summary']


def test_actor_three_entries_one_directory(current_actor_context):
    current_actor_context.feed(
        BlackListCA(
            source="/blacklist/badcert.ca",
            sourceDir="/blacklist",
            target="/blocklist/badcert.ca",
            targetDir="/blocklist"
        ),
        BlackListCA(
            source="/blacklist/badcert2.ca",
            sourceDir="/blacklist",
            target="/blocklist/badcert2.ca",
            targetDir="/blocklist"
        ),
        BlackListCA(
            source="/blacklist/badcert3.ca",
            sourceDir="/blacklist",
            target="/blocklist/badcert3.ca",
            targetDir="/blocklist"
        ),
    )
    current_actor_context.run()
    r = current_actor_context.consume(Report)
    assert r
    assert ('/blacklist/badcert.ca, /blacklist/badcert2.ca and '
            '/blacklist/badcert3.ca will be moved to /blocklist and '
            '/blacklist will be deleted') in r[0].report['summary']


def test_actor_two_entries_two_directories(current_actor_context):
    current_actor_context.feed(
        BlackListCA(
            source="/blacklist/badcert.ca",
            sourceDir="/blacklist",
            target="/blocklist/badcert.ca",
            targetDir="/blocklist"
        ),
        BlackListCA(
            source="/private/blacklist/badcert2.ca",
            sourceDir="/private/blacklist",
            target="/private/blocklist/badcert2.ca",
            targetDir="/private/blocklist"
        )
    )
    current_actor_context.run()
    r = current_actor_context.consume(Report)
    assert r
    assert ('/blacklist/badcert.ca will be moved to /blocklist '
            'and /private/blacklist/badcert2.ca will be moved to '
            '/private/blocklist and /blacklist and /private/blacklist '
            'will be deleted') in r[0].report['summary']


def test_actor_three_entries_tree_directories(current_actor_context):
    current_actor_context.feed(
        BlackListCA(
            source="/blacklist/badcert.ca",
            sourceDir="/blacklist",
            target="/blocklist/badcert.ca",
            targetDir="/blocklist"
        ),
        BlackListCA(
            source="/private/blacklist/badcert2.ca",
            sourceDir="/private/blacklist",
            target="/private/blocklist/badcert2.ca",
            targetDir="/private/blocklist"
        ),
        BlackListCA(
            source="/public/blacklist/badcert3.ca",
            sourceDir="/public/blacklist",
            target="/public/blocklist/badcert3.ca",
            targetDir="/public/blocklist"
        )
    )
    current_actor_context.run()
    r = current_actor_context.consume(Report)
    assert r
    assert ('/blacklist/badcert.ca will be moved to /blocklist, '
            '/private/blacklist/badcert2.ca will be moved to '
            '/private/blocklist and /public/blacklist/badcert3.ca '
            'will be moved to /public/blocklist and /blacklist, '
            '/private/blacklist and /public/blacklist will be deleted') in r[0].report['summary']
