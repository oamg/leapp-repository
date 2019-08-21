from leapp.models import Report, SkippedRepositories


def test_skipped_repos(current_actor_context):
    reported_packages = ['pkg_a', 'pkg_b', 'pkg_c']
    reported_repos = ['repo_a', 'repo_b', 'repo_c']
    current_actor_context.feed(
        SkippedRepositories(
            packages=list(reported_packages),
            repos=list(reported_repos)
        )
    )

    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert reports
    assert len(reports) == 1
    report_fields = reports[0].report
    for pkg in reported_packages:
        assert '\n- {}'.format(pkg) in report_fields['summary']
    for repo in reported_repos:
        assert '\n- {}'.format(repo) in report_fields['summary']


def test_skipped_just_repos(current_actor_context):
    reported_repos = ['repo_a', 'repo_b', 'repo_c']
    current_actor_context.feed(
        SkippedRepositories(
            packages=[],
            repos=list(reported_repos)
        )
    )

    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert reports
    assert len(reports) == 1
    report_fields = reports[0].report
    for repo in reported_repos:
        assert '\n- {}'.format(repo) in report_fields['summary']


def test_skipped_repos_empty(current_actor_context):
    current_actor_context.feed(
        SkippedRepositories(
            packages=[],
            repos=[]
        )
    )
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert not reports


def test_skipped_repos_no_repos(current_actor_context):
    current_actor_context.feed(
        SkippedRepositories(
            packages=['woot'],
            repos=[]
        )
    )
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert not reports


def test_skipped_repos_no_message(current_actor_context):
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert not reports
