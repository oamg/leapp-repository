import os
from leapp.utils.repository import find_repository_basedir
from leapp.repository.scan import find_and_scan_repositories


def pytest_sessionstart(session):
    actor_path = os.environ.get('LEAPP_TESTED_ACTOR', None)
    if not actor_path:
        return
    repo = find_and_scan_repositories(find_repository_basedir(actor_path), include_locals=True)
    repo.load()

    actor = None
    # find which actor is being tested
    for a in repo.actors:
        if a.full_path == actor_path.rstrip('/'):
            actor = a
            break

    if not actor:
        return

    # load actor context so libraries can be imported on module level
    session.leapp_repository = repo
    session.actor_context = actor.injected_context()
    session.actor_context.__enter__()
