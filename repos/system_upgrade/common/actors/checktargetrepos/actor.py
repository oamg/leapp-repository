from leapp.actors import Actor
from leapp.libraries.actor import checktargetrepos
from leapp.models import CustomTargetRepositoryFile, Report, RHUIInfo, TargetRepositories
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class Checktargetrepos(Actor):
    """
    Check whether target yum repositories are specified.

    RHSM | RHUI | ER | CTR | CTRF || result
    -----+------+----+-----+------++-------
     Yes | ---- | -- | --- | ---- || -
    -----+------+----+-----+------++-------
     No  | Yes  | -- | --- | ---- || -
    -----+------+----+-----+------++-------
     No  | No   | -- | No  | No   || inhibit
    -----+------+----+-----+------++-------
     No  | No   | -- | No  | Yes  || inhibit
    -----+------+----+-----+------++-------
     No  | No   | No | Yes | No   || warn/report info
    -----+------+----+-----+------++-------
     No  | No   | No | Yes | Yes  || -
    -----+------+----+-----+------++-------
     No  | No   | Yes| Yes | No   || -
    -----+------+----+-----+------++-------
     No  | No   | Yes| Yes | Yes  || -

       ER   - config.get_env('LEAPP_ENABLE_REPOS') is non-empty
       CTR  - CustomTargetRepositories found
       CTRF - the expected CustomTargetRepositoryFile found
       RHSM - RHSM is used (it is not skipped)
       RHUI - RHUIInfo msg is consumed

    This is not 100 % reliable check. This cover just the most obvious cases
    that are expected to fail. Reporting of such issues in this way, here,
    will be probably much more clear, without additional errors that could
    be raised.
    """

    name = 'checktargetrepos'
    consumes = (CustomTargetRepositoryFile, TargetRepositories, RHUIInfo)
    produces = (Report)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        checktargetrepos.process()
