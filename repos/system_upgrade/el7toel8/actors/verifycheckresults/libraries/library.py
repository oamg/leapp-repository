from leapp.exceptions import RequestStopAfterPhase
from leapp.libraries.stdlib import api
from leapp.reporting import Report


def check():
    if [msg for msg in api.consume(Report) if 'inhibitor' in msg.report.get('flags', [])]:
        raise RequestStopAfterPhase()
