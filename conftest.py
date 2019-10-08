import os

def load_repo(path):
    """
    Load repository on demand.

    Do not require paths initialized if no environment is set.
    Allows some parts to be tested without working leapp installation.
    """
    from leapp.utils.repository import find_repository_basedir
    from leapp.repository.scan import find_and_scan_repositories

    repo = find_and_scan_repositories(find_repository_basedir(path), include_locals=True)
    repo.load()
    return repo
        

def pytest_sessionstart(session):

    actor_path = os.environ.get('LEAPP_TESTED_ACTOR', None)
    library_path = os.environ.get('LEAPP_TESTED_LIBRARY', None)

    if actor_path:
        repo = load_repo(actor_path)

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
    elif library_path:
        load_repo(library_path)
        os.chdir(library_path)
