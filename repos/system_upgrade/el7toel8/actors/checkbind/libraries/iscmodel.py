from leapp import reporting
from leapp.libraries.common import isccfg
from leapp.libraries.stdlib import api
from leapp.models import BindConfigIssuesModel, BindFacts


def add_statement(statement, state):
    """Add searched statement to found issues."""

    stmt_text = statement.serialize_skip(' ')
    name = statement.var(0).value()
    if name in state:
        state[name].append((stmt_text, statement.config.path))
    else:
        state[name] = [(stmt_text, statement.config.path)]


def find_dnssec_lookaside(statement, state):
    try:
        arg = statement.var(1)
        if not (arg.type() == arg.TYPE_BARE and arg.value() == 'no'):
            # auto or yes statement
            # dnssec-lookaside "." trust-anchor "dlv.isc.org";
            add_statement(statement, state)
    except IndexError:
        api.current_logger().warning('Unexpected statement format: "%s"',
                                     statement.serialize_skip(' '))


def convert_to_issues(statements):
    """Produce list of offending statements in set of files.

    :param statements: one item from list created by add_statement
    """

    files = dict()
    for statement, path in statements:
        if path in files:
            files[path].update(statement)
            if statement not in files[path].statements:
                files[path].statements.append(statement)
        else:
            files[path] = set(statement)
    values = list()
    for path in files:
        values.append(BindConfigIssuesModel(path=path, statements=list(files[path])))
    return values


def convert_found_state(state, files):
    """Convert find state results to facts.

    Check found statements and create facts from them."""

    dnssec_lookaside = None
    if 'dnssec-lookaside' in state:
        dnssec_lookaside = convert_to_issues(state['dnssec-lookaside'])

    return BindFacts(config_files=files,
                     modified_files=[],
                     dnssec_lookaside=dnssec_lookaside,
                     listen_on_v6_missing='listen-on-v6' not in state)


def get_facts(path, log=None):
    """Find issues in configuration files.

    Report used configuration files and wrong statements in each file.
    """

    find_calls = {
        'dnssec-lookaside': find_dnssec_lookaside,
        'listen-on-v6': add_statement,
    }

    parser = isccfg.IscConfigParser(path)
    state = {}
    files = set()

    for cfg in parser.FILES_TO_CHECK:
        parser.walk(cfg.root_section(), find_calls, state)
        files.add(cfg.path)

        api.current_logger().debug('Found state: "%s", files: "%s"',
                                   repr(state), files)

    facts = convert_found_state(state, list(files))
    return facts


def make_report(facts):
    """Make report message from gathered facts."""
    summary_messages = []
    report = []
    if facts.dnssec_lookaside:
        summary_messages.append('BIND configuration contains no longer accepted statements: dnssec-lookaside.')
    if facts.listen_on_v6_missing:
        summary_messages.append('Default value of listen-on-v6 have changed, but it is not present in configuration.'
                                ' named service will now listen on INET6 sockets also.')

    if summary_messages:
        summary = ' '.join(summary_messages)
        report.extend([
            reporting.Title('BIND configuration issues found'),
            reporting.Summary(summary),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.SERVICES, reporting.Groups.NETWORK]),
        ])

    return report
