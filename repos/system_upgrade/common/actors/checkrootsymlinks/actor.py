from leapp.actors import Actor
from leapp.libraries.actor import checkrootsymlinks
from leapp.models import Report, RootDirectory
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckRootSymlinks(Actor):
    """
    Check if the symlinks /bin and /lib are relative, not absolute.

    After reboot, dracut fails if the links are absolute.
    """

    name = 'check_root_symlinks'
    consumes = (RootDirectory,)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        checkrootsymlinks.process()
