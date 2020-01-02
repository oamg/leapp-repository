from leapp.libraries.stdlib import api
from leapp.models import DialogModel
from leapp import reporting


def check_dialogs(inhibit_if_no_userchoice=True):
    results = list(api.consume(DialogModel))
    for dialog in results:
        sections = dialog.answerfile_sections.split(',')
        dialog_resources = [reporting.RelatedResource('dialog', s) for s in sections]
        dialogs_remediation = ('Please register user choices with leapp answer cli command or by manually editing '
                               'the answerfile.')
        report_data = [reporting.Title('Dialog choice required'),
                       reporting.Severity(reporting.Severity.HIGH),
                       reporting.Summary(
                           'One or more sections in answerfile are missing recorded user choices: {}'.format(
                               '\n'.join(sections))),
                       reporting.Flags([reporting.Flags.INHIBITOR] if inhibit_if_no_userchoice else []),
                       reporting.Remediation(hint=dialogs_remediation)]
        reporting.create_report(report_data + dialog_resources)
