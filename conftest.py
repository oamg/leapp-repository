import os

from leapp.repository.scan import find_and_scan_repositories


def pytest_sessionstart(session):
    actor_path = os.environ.get('LEAPP_TESTED_ACTOR', None)
    if not actor_path:
        return
    repo = find_and_scan_repositories(('/'.join(actor_path.split('/')[:-2])), include_locals=True)
    repo.load()

    actor = None
    # find which actor is being tested
    for a in repo.actors:
        if a.full_path == actor_path:
            actor = a
            break

    if not actor:
        return

    # load actor context so libraries can be imported on module level
    session.actor_context = actor.injected_context()
    session.actor_context.__enter__()
