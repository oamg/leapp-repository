import json


class PlainTextReport:
    def header(self, report_file):
        pass

    def write(self, result, report_file):
        report_file.write('Severity: ' + result.severity + '\n')
        report_file.write('Title: ' + result.title + '\n')
        report_file.write('Summary: ' + result.detail['summary'] + '\n')
        if result.detail.get('remediation'):
            report_file.write('Remediation: ' + result.detail['remediation'] + '\n')
        report_file.write('-' * 40 + '\n')

    def footer(self, report_file):
        pass


class JSONReport:
    _first_entry = True

    def header(self, report_file):
        report_file.write('[')

    def write(self, result, report_file):

        data = json.dumps(result.dump())

        if self._first_entry:
            report_file.write(data)
            self._first_entry = False
        else:
            report_file.write(',' + data)

    def footer(self, report_file):
        report_file.write(']\n')


def generate_report(results, path):
    reporter = None

    if path.endswith('.txt'):
        reporter = PlainTextReport()

    if path.endswith('.json'):
        reporter = JSONReport()

    if not reporter:
        return 'Report format not supported.'

    with open(path, 'w') as report_file:
        reporter.header(report_file)

        for r in results:
            reporter.write(r, report_file)

        reporter.footer(report_file)

    return None
