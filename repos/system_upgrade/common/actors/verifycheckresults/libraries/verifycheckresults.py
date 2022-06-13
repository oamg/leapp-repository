from leapp.exceptions import RequestStopAfterPhase
from leapp.libraries.stdlib import api
from leapp.reporting import Report
from leapp.utils.report import is_inhibitor


def check():
    if [msg for msg in api.consume(Report) if is_inhibitor(msg.report)]:
        raise RequestStopAfterPhase()
