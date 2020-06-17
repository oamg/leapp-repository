import logging

from leapp.repository.scan import find_and_scan_repositories
from leapp.utils.repository import find_repository_basedir

logger = logging.getLogger(__name__)
logging.getLogger("asyncio").setLevel(logging.INFO)
logging.getLogger("parso").setLevel(logging.INFO)


def pytest_collectstart(collector):
    if collector.nodeid:
        current_repo_basedir = find_repository_basedir(collector.nodeid)
        # loading the current repo
        if (
            not hasattr(collector.session, "leapp_repository")
            or current_repo_basedir != collector.session.repo_base_dir
        ):
            repo = find_and_scan_repositories(
                find_repository_basedir(collector.nodeid), include_locals=True
            )
            repo.load(skip_actors_discovery=True)
            collector.session.leapp_repository = repo
            collector.session.repo_base_dir = current_repo_basedir

        # we're forcing the actor context switch only when traversing new
        # actor
        if "/actors/" in str(collector.fspath) and (
            not hasattr(collector.session, "current_actor_path")
            or collector.session.current_actor_path
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
