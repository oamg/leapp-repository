from leapp.actors import Actor
from leapp.libraries.actor import scansourcefiles
from leapp.models import TrackedFilesInfoSource
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanSourceFiles(Actor):
    """
    Scan files (explicitly specified) of the source system.

    If an actor require information about a file, like whether it's installed,
    modified, etc. It can be added to the list of files to be tracked, so no
    extra actor is required to be created to provide just that one information.

    The scan of all changed files tracked by RPMs is very expensive. So we rather
    provide this possibility to simplify the work for others.

    See lists defined in the private library.
    """
    # TODO(pstodulk): in some cases could be valuable to specify an rpm name
    # and provide information about all changed files instead. Both approaches
    # have a little bit different use-cases and expectations. In the second
    # case it would be good solution regarding track of leapp-repository
    # changed files.

    name = 'scan_source_files'
    consumes = ()
    produces = (TrackedFilesInfoSource,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        scansourcefiles.process()
