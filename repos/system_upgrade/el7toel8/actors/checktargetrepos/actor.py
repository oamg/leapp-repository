from leapp.actors import Actor
from leapp.libraries.actor import library
from leapp.models import CustomTargetRepositoryFile, Report, TargetRepositories
from leapp.tags import IPUWorkflowTag, ChecksPhaseTag


class Checktargetrepos(Actor):
    """
    Check whether target yum repositories are specified.

    RHSM | CTR | CTRF || result
    -----+-----+------++-------
     Yes | --- | ---- || -
    -----+-----+------++-------
     No  | No  | No   || inhibit
    -----+-----+------++-------
     No  | No  | Yes  || inhibit
    -----+-----+------++-------
     No  | Yes | No   || warn/report info
    -----+-----+------++-------
     No  | Yes | Yes  || -

       CTR  - CustomTargetRepositories found
       CTRF - the expected CustomTargetRepositoryFile found
       RHSM - RHSM is used (it is not skipped)

    This is not 100 % reliable check. This cover just the most obvious cases
    that are expected to fail. Reporting of such issues in this way, here,
    will be probably much more clear, without additional errors that could
    be raised.
    """

    name = 'checktargetrepos'
    consumes = (CustomTargetRepositoryFile, TargetRepositories)
    produces = (Report)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        library.process()
