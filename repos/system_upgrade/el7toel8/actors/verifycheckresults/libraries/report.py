import json


class PlainTextReport:
    def header(self, report_file):
        pass

    def write(self, result, report_file):
        report_file.write('Severity: ' + result.severity + '\n')
        report_file.write('Result: ' + result.result + '\n')
        report_file.write('Summary: ' + result.summary + '\n')
        report_file.write('Details: ' + result.details + '\n')
        if result.solutions:
            report_file.write('Solutions: ' + result.solutions + '\n')
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
        return 'Report format not supported'

    with open(path, 'w') as report_file:
        reporter.header(report_file)

        for r in results:
            reporter.write(r, report_file)

        reporter.footer(report_file)

    return None
