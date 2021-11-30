import re

SPAMC_CONFIG_FILE = '/etc/mail/spamassassin/spamc.conf'
SPAMASSASSIN_SERVICE_OVERRIDE = '/etc/systemd/system/spamassassin.service'
SYSCONFIG_SPAMASSASSIN = '/etc/sysconfig/spamassassin'
SYSCONFIG_VARIABLE = 'SPAMDOPTIONS'
SPAMD_SHORTOPTS_NOARG = "ch46LlxPQqVv"
""" All short options in spamd that do not accept an argument, excluding -d. """


def parse_sysconfig_spamassassin(content):
    """
    Splits up a spamassassin sysconfig file into three parts and returns those parts:
    1. Beginning of the file up to the SPAMDOPTIONS assignment
    2. The assignment to the SPAMDOPTIONS variable (this is the assignment
       that takes effect, i.e. the last assignment to the variable)
    3. End of the file after the SPAMDOPTIONS assignment
    """
    line_continues = False
    is_assignment = False
    assignment_start = None
    assignment_end = None
    lines = content.split('\n')
    for ix, line in enumerate(lines):
        is_assignment = ((is_assignment and line_continues) or
                         (not (not is_assignment and line_continues) and
                          re.match(r'\s*' + SYSCONFIG_VARIABLE + '=', line)))
        if is_assignment:
            if line_continues:
                assignment_end += 1
            else:
                assignment_start = ix
                assignment_end = ix + 1
        line_continues = line.endswith('\\')

    if assignment_start is None:
        return content, '', ''
    assignment = ''
    for line in lines[assignment_start:assignment_end - 1]:
        assignment += line[:-1]
    assignment += lines[assignment_end - 1]
    pre_assignment = '\n'.join(lines[:assignment_start])
    post_assignment = '\n'.join(lines[assignment_end:])
    return pre_assignment, assignment, post_assignment
