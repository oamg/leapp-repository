from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import isccfg
from leapp.libraries.stdlib import api, CalledProcessError, run

# Callback for walk function
callbacks = {
    'dnssec-lookaside': isccfg.ModifyState.callback_comment_out,
}


def paths_from_issues(issues):
    """Extract paths from list of BindConfigIssuesModel."""
    return [issue.path for issue in issues]


def parser_file(parser, path):
    for cfg in parser.FILES_TO_CHECK:
        if cfg.path == path:
            return cfg
    return None


def make_backup(path, backup_suffix='.leapp'):
    """Make backup of a file before modification."""
    backup_path = path + backup_suffix
    try:
        run(['cp', '--preserve=all', path, backup_path])
    except CalledProcessError as exc:
        raise StopActorExecutionError(
            'Could not create a backup copy',
            details={'details': 'An exception during backup raised {}'.format(str(exc))}
        )


def update_section(parser, section):
    """Modify one section.

    :type section: ConfigSection
    """
    state = isccfg.ModifyState()
    parser.walk(section, callbacks, state)
    state.finish(section)
    return state.content()


def update_config(parser, cfg):
    """Modify contents of file according to rules.

    :type cfg: ConfigFile
    :returns str: Modified config contents
    """
    return update_section(parser, cfg.root_section())


def update_file(parser, path, write=True):
    """Prepare modified content for the file, make backup and rewrite it.

    :param parser: IscConfigParser
    :param path: String with path to a file
    :param log: Log instance with debug(str) method or None
    :param write: True to allow file modification, false to only return modification status
    """
    cfg = parser_file(parser, path)
    modified = update_config(parser, cfg)
    if modified != cfg.buffer:
        api.current_logger().debug('%s needs modification', path)
        if write:
            make_backup(path)
            with open(path, 'w') as f:
                f.write(modified)
            api.current_logger().debug('%s updated to size %d', path, len(modified))
        return True
    return False


def update_facts(facts, path='/etc/named.conf'):
    """Parse and update all files according to supplied facts.

    :param facts: BindFacts instance
    :param path: String to main configuration file
    :returns: number of modified files
    """
    parser = isccfg.IscConfigParser(path)
    modified_files = set()
    if facts.dnssec_lookaside:
        for model in facts.dnssec_lookaside:
            if update_file(parser, model.path):
                modified_files.add(model.path)
    facts.modified_files = list(modified_files)
