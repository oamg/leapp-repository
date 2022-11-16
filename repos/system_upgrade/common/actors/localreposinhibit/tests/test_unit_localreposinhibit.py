import pytest

from leapp.models import (
    RepositoryData,
    RepositoryFile,
    TargetOSInstallationImage,
    TMPTargetRepositoriesFacts,
    UsedTargetRepositories,
    UsedTargetRepository
)
from leapp.snactor.fixture import ActorContext


@pytest.mark.parametrize(
    ("baseurl", "mirrorlist", "metalink", "exp_msgs_len"),
    [
        ("file:///root/crb", None, None, 1),
        ("http://localhost/crb", None, None, 0),
        (None, "file:///root/crb", None, 1),
        (None, "http://localhost/crb", None, 0),
        (None, None, "file:///root/crb", 1),
        (None, None, "http://localhost/crb", 0),
        ("http://localhost/crb", "file:///root/crb", None, 1),
        ("file:///root/crb", "http://localhost/crb", None, 0),
        ("http://localhost/crb", None, "file:///root/crb", 1),
        ("file:///root/crb", None, "http://localhost/crb", 0),
    ],
)
def test_unit_localreposinhibit(current_actor_context, baseurl, mirrorlist, metalink, exp_msgs_len):
    """Ensure the Report is generated when local path is used as a baseurl.

    :type current_actor_context: ActorContext
    """
    with pytest.deprecated_call():
        current_actor_context.feed(
            TMPTargetRepositoriesFacts(
                repositories=[
                    RepositoryFile(
                        file="the/path/to/some/file",
                        data=[
                            RepositoryData(
                                name="BASEOS",
                                baseurl=(
                                    "http://example.com/path/to/repo/BaseOS/x86_64/os/"
                                ),
                                repoid="BASEOS",
                            ),
                            RepositoryData(
                                name="APPSTREAM",
                                baseurl=(
                                    "http://example.com/path/to/repo/AppStream/x86_64/os/"
                                ),
                                repoid="APPSTREAM",
                            ),
                            RepositoryData(
                                name="CRB", repoid="CRB", baseurl=baseurl,
                                mirrorlist=mirrorlist, metalink=metalink
                            ),
                        ],
                    )
                ]
            )
        )
    current_actor_context.feed(
        UsedTargetRepositories(
            repos=[
                UsedTargetRepository(repoid="BASEOS"),
                UsedTargetRepository(repoid="CRB"),
            ]
        )
    )
    current_actor_context.run()
    assert len(current_actor_context.messages()) == exp_msgs_len


def test_upgrade_not_inhibited_if_iso_used(current_actor_context):
    repofile = RepositoryFile(file="path/to/some/file",
                              data=[RepositoryData(name="BASEOS", baseurl="file:///path", repoid="BASEOS")])
    current_actor_context.feed(TMPTargetRepositoriesFacts(repositories=[repofile]))
    current_actor_context.feed(UsedTargetRepositories(repos=[UsedTargetRepository(repoid="BASEOS")]))
    current_actor_context.feed(TargetOSInstallationImage(path='', mountpoint='', repositories=[]))
