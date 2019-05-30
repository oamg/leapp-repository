from leapp.actors import Actor
from leapp.models import InstalledRedHatSignedRPM
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag
from leapp.reporting import Report
from leapp.libraries.common.reporting import report_with_remediation


class CheckGrep(Actor):
    """
    Check if Grep is installed. If yes, write information about non-compatible changes.
    """

    name = 'checkgrep'
    consumes = (InstalledRedHatSignedRPM,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        for fact in self.consume(InstalledRedHatSignedRPM):
            for rpm in fact.items:
                if rpm.name == 'grep':
                    report_with_remediation(
                        title='Grep has incompatible changes in the next major version',
                        summary='If a file contains data improperly encoded for the current locale, and this is '
                                'discovered before any of the file\'s contents are output, grep now treats the file '
                                'as binary.\n'
                                'The \'grep -P\' no longer reports an error and exits when given invalid UTF-8 data. '
                                'Instead, it considers the data to be non-matching.\n'
                                'In locales with multibyte character encodings other than UTF-8, grep -P now reports '
                                'an error and exits instead of misbehaving.\n'
                                'When searching binary data, grep now may treat non-text bytes as line terminators. '
                                'This can boost performance significantly.\n'
                                'The \'grep -z\' no longer automatically treats the byte \'\\200\' as binary data.\n'
                                'Context no longer excludes selected lines omitted because of -m. For example, '
                                '\'grep "^" -m1 -A1\' now outputs the first two input lines, not just the first '
                                'line.\n',
                        remediation='Please update your scripts to be compatible with the changes.',
                        severity='low')
                    return
