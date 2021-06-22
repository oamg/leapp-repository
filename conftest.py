import logging
import os

from leapp.repository.manager import RepositoryManager
from leapp.repository.scan import find_and_scan_repositories
from leapp.utils.repository import find_repository_basedir, get_repository_id

logger = logging.getLogger(__name__)
logging.getLogger("asyncio").setLevel(logging.INFO)
logging.getLogger("parso").setLevel(logging.INFO)


def _load_and_add_repo(manager, repo_path):
    repo = find_and_scan_repositories(
        repo_path,
        include_locals=True
    )
    unloaded = set()
    loaded = {r.repo_id for r in manager.repos}
    if hasattr(repo, 'repos'):
        for repo in repo.repos:
            if not manager.repo_by_id(repo.repo_id):
                manager.add_repo(repo)
                unloaded.add(repo.repo_id)
    else:
        manager.add_repo(repo)
    if not loaded:
        manager.load(skip_actors_discovery=True)
    else:
        for repo_id in unloaded:
            manager.repo_by_id(repo_id).load(skip_actors_discovery=True)


def pytest_collectstart(collector):
    if collector.nodeid:
        current_repo_basedir = find_repository_basedir(str(collector.fspath))
        if not hasattr(collector.session, "leapp_repository"):
            collector.session.leapp_repository = RepositoryManager()
            collector.session.repo_base_dir = current_repo_basedir
            _load_and_add_repo(collector.session.leapp_repository, current_repo_basedir)
        else:
            if not collector.session.leapp_repository.repo_by_id(
                get_repository_id(current_repo_basedir)
            ):
                _load_and_add_repo(collector.session.leapp_repository, current_repo_basedir)

        # we're forcing the actor context switch only when traversing new
        # actor
        if "/actors/" in str(collector.fspath) and (
            not hasattr(collector.session, "current_actor_path")
            or collector.session.current_actor_path + os.sep
            not in str(collector.fspath)
        ):
            actor = None
            for a in collector.session.leapp_repository.actors:
                if a.full_path == collector.fspath.dirpath().dirname:
                    actor = a
                    break

            if not actor:
                logger.info("No actor found, exiting collection...")
                return
            # we need to tear down the context from the previous
            # actor
            try:
                collector.session.current_actor_context.__exit__(
                    None, None, None
                )
            except AttributeError:
                pass
            else:
                logger.info(
                    "Actor %r context teardown complete",
                    collector.session.current_actor.name,
                )

            logger.info("Injecting actor context for %r", actor.name)
            collector.session.current_actor = actor
            collector.session.current_actor_context = actor.injected_context()
            collector.session.current_actor_context.__enter__()
            collector.session.current_actor_path = (
                collector.session.current_actor.full_path
            )
            logger.info("Actor %r context injected", actor.name)


def pytest_runtestloop(session):
    try:
        session.current_actor_context.__exit__(None, None, None)
        logger.info(
            "Actor %r context teardown complete", session.current_actor.name,
        )
    except AttributeError:
        pass
