from leapp.libraries.stdlib import api
from leapp.models import DialogModel
from leapp import reporting


def check_dialogs(inhibit_if_no_userchoice=True):
    results = list(api.consume(DialogModel))
    for dialog in results:
        sections = dialog.answerfile_sections
        summary = ('One or more sections in answerfile are missing user choices: {}\n'
                   'For more information consult https://leapp.readthedocs.io/en/latest/dialogs.html')
        dialog_resources = [reporting.RelatedResource('dialog', s) for s in sections]
        dialogs_remediation = ('Please register user choices with leapp answer cli command or by manually editing '
                               'the answerfile.')
        # FIXME: Enable more choices once we can do multi-command remediations
        cmd_remediation = [['leapp', 'answer', '--section', "{}={}".format(s, choice)]
                           for s, choices in dialog.answerfile_sections.items() for choice in choices[:1]]
        report_data = [reporting.Title('Missing required answers in the answer file'),
                       reporting.Severity(reporting.Severity.HIGH),
                       reporting.Summary(summary.format('\n'.join(sections))),
                       reporting.Flags([reporting.Flags.INHIBITOR] if inhibit_if_no_userchoice else []),
                       reporting.Remediation(hint=dialogs_remediation, commands=cmd_remediation),
                       reporting.Key(dialog.key)]
        reporting.create_report(report_data + dialog_resources)
