from leapp.libraries.stdlib import api
from leapp.reporting import Report


def check():
    results = list(api.consume(Report))
    for error in [msg for msg in results if 'inhibitor' in msg.report.get('flags', [])]:
        api.report_error(error.report['title'])
