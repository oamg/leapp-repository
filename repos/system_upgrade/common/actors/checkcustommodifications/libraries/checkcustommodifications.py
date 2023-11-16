from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import CustomModifications

FMT_LIST_SEPARATOR = "\n    - "


def _pretty_files(messages):
    """
    Return formatted string of discovered files from obtained CustomModifications messages.
    """
    flist = []
    for msg in messages:
        actor = ' (Actor: {})'.format(msg.actor_name) if msg.actor_name else ''
        flist.append(
            '{sep}{filename}{actor}'.format(
                sep=FMT_LIST_SEPARATOR,
                filename=msg.filename,
                actor=actor
            )
        )
    return ''.join(flist)


def _is_modified_config(msg):
    # NOTE(pstodulk):
    # We are interested just about modified files for now. Having new created config
    # files is not so much important for us right now, but in future it could
    # be changed.
    if msg.component and msg.component == 'configuration':
        return msg.type == 'modified'
    return False


def _create_report(title, summary, hint, links=None):
    report_parts = [
        reporting.Title(title),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.UPGRADE_PROCESS]),
        reporting.RemediationHint(hint)
    ]
    if links:
        report_parts += links
    reporting.create_report(report_parts)


def check_configuration_files(msgs):
    filtered_msgs = [m for m in msgs if _is_modified_config(m)]
    if not filtered_msgs:
        return
    title = 'Detected modified configuration files in leapp configuration directories.'
    summary = (
        'We have detected that some configuration files related to leapp or'
        ' upgrade process have been modified. Some of these changes could be'
        ' intended (e.g. modified repomap.json file in case of private cloud'
        ' regions or customisations done on used Satellite server) so it is'
        ' not always needed to worry about them. However they can impact'
        ' the in-place upgrade and it is good to be aware of potential problems'
        ' or unexpected results if they are not intended.'
        '\nThe list of modified configuration files:{files}'
        .format(files=_pretty_files(filtered_msgs))
    )
    hint = (
        'If some of changes in listed configuration files have not been intended,'
        ' you can restore original files by following procedure:'
        '\n1. Remove (or back up) modified files that you want to restore.'
        '\n2. Reinstall packages which owns these files.'
    )
    _create_report(title, summary, hint)


def _is_modified_code(msg):
    if msg.component not in ['framework', 'repository']:
        return False
    return msg.type == 'modified'


def check_modified_code(msgs):
    filtered_msgs = [m for m in msgs if _is_modified_code(m)]
    if not filtered_msgs:
        return
    title = 'Detected modified files of the in-place upgrade tooling.'
    summary = (
        'We have detected that some files of the tooling processing the in-place'
        ' upgrade have been modified. Note that such modifications can be allowed'
        ' only after consultation with Red Hat - e.g. when support suggests'
        ' the change to resolve discovered problem.'
        ' If these changes have not been approved by Red Hat, the in-place upgrade'
        ' is unsupported.'
        '\nFollowing files have been modified:{files}'
        .format(files=_pretty_files(filtered_msgs))
    )
    hint = 'To restore original files reinstall related packages.'
    _create_report(title, summary, hint)


def check_custom_actors(msgs):
    filtered_msgs = [m for m in msgs if m.type == 'custom']
    if not filtered_msgs:
        return
    title = 'Detected custom leapp actors or files.'
    summary = (
        'We have detected installed custom actors or files on the system.'
        ' These can be provided e.g. by third party vendors, Red Hat consultants,'
        ' or can be created by users to customize the upgrade (e.g. to migrate'
        ' custom applications).'
        ' This is allowed and appreciated. However Red Hat is not responsible'
        ' for any issues caused by these custom leapp actors.'
        ' Note that upgrade tooling is under agile development which could'
        ' require more frequent update of custom actors.'
        '\nThe list of custom leapp actors and files:{files}'
        .format(files=_pretty_files(filtered_msgs))
    )
    hint = (
        'In case of any issues connected to custom or third party actors,'
        ' contact vendor of such actors. Also we suggest to ensure the installed'
        ' custom leapp actors are up to date, compatible with the installed'
        ' packages.'
    )
    links = [
        reporting.ExternalLink(
            url='https://red.ht/customize-rhel-upgrade',
            title='Customizing your Red Hat Enterprise Linux in-place upgrade'
        )
    ]

    _create_report(title, summary, hint, links)


def report_any_modifications():
    modifications = list(api.consume(CustomModifications))
    if not modifications:
        # no modification detected
        return
    check_custom_actors(modifications)
    check_configuration_files(modifications)
    check_modified_code(modifications)
