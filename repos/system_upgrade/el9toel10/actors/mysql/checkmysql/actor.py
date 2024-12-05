from leapp.actors import Actor
from leapp.libraries.actor import checkmysql
from leapp.models import MySQLConfiguration, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class MySQLCheck(Actor):
    """
    Actor checking for output produced by scanmysql actor.

    If no deprecated options/arguments are in use, we warn user that MySQL
    server is installed and that more steps might be needed after upgrade with
    link to article.

    If there are deprecated options/arguments found we warn user that MySQL
    server is installed and more steps ARE needed. They can be done either
    before or after upgrading, but if done after MySQL server won't be
    operational until config is fixed.
    """
    name = 'mysql_check'
    consumes = (MySQLConfiguration,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self) -> None:
        checkmysql.process()
