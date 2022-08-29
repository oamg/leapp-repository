import re

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api

# The openssl configuration file
# TODO copied from opensslconfigscanner/libraries/readconf.py
CONFIG = '/etc/pki/tls/openssl.cnf'

LEAPP_COMMENT = '# Modified by leapp during upgrade to RHEL 9\n'
APPEND_STRING = (
    '[provider_sect]\n'
    'default = default_sect\n'
    '##legacy = legacy_sect\n'
    '\n'
    '[default_sect]\n'
    'activate = 1\n'
    '\n'
    '##[legacy_sect]\n'
    '##activate = 1\n'
)


def _add_lines(lines, add):
    """
    Add lines to the list of lines. Breaking possible newlines onto separate items
    """
    for l in add.split("\n"):
        lines.append("{}\n".format(l))
    return lines


class NotFoundException(Exception):
    pass


def _replace(lines, search, replace, comment=None, backup=False, fail_on_error=True):
    """
    Replace pattern with new value with optional backup

    Replace the lines (ignoring leading and trailing whitespace) matching `search` regex
    in the given file (as `lines` collected using readlines()) with the `replace` line optional
    comment is added on line preceding the change.
    """
    res = []
    found = False
    for line in lines:
        if re.search(search, line.strip()):
            if comment:
                res.append(comment)
            if backup:
                res.append("# {}".format(line))
            res = _add_lines(res, replace)
            found = True
        else:
            res.append(line)
    if not found and fail_on_error:
        raise NotFoundException("The pattern {} not found.".format(search))
    return res


def _append(lines, add, comment=None):
    """
    Append a line to the existing list with optional comment
    """
    if comment:
        lines.append(comment)
    return _add_lines(lines, add)


def _modify_file(f, fail_on_error=True):
    """
    Modify the openssl configuration file to accommodate el8toel9 changes
    """
    lines = f.readlines()
    lines = _replace(lines, r"openssl_conf\s*=\s*default_modules",
                     "openssl_conf = openssl_init",
                     LEAPP_COMMENT, True, fail_on_error)
    lines = _replace(lines, r"\[\s*default_modules\s*\]",
                     "[openssl_init]\n"
                     "providers = provider_sect",
                     LEAPP_COMMENT, True, fail_on_error)
    lines = _append(lines, APPEND_STRING, LEAPP_COMMENT)
    f.seek(0)
    f.write(''.join(lines))


def process(openssl_messages):
    """
    Process the changes needed to update configuration file

    Steps:
     * read the file
     * replace the required chunks
     * write the file
    """
    config = next(openssl_messages, None)
    if list(openssl_messages):
        api.current_logger().warning('Unexpectedly received more than one OpenSslConfig message.')
    if not config:
        raise StopActorExecutionError(
            'Could not check openssl configuration', details={'details': 'No OpenSslConfig facts found.'}
        )

    # If the configuration file was not modified, the rpm update will bring the new
    # changes by itself -- do not change the file now.
    if not config.modified:
        return

    # otherwise modify the file as announced in actors/opensslconfigcheck/actor.py
    api.current_logger().debug('Modifying the {}.'.format(CONFIG))
    try:
        with open(CONFIG, 'r+') as f:
            _modify_file(f)
    except (OSError, IOError, NotFoundException) as error:
        api.current_logger().error('Failed to modify the file {}: {} '.format(CONFIG, error))
        reporting.create_report([
            reporting.Title('Could not modify {}: {}'.format(CONFIG, error)),
            reporting.Summary(
                'The original version was kept in place.'
                'The OpenSSL should keep working as expected in most of the cases, but you '
                'might encounter some issues if you need to use custom providers. Consider '
                'updating the configuration manually. For reference, see the openssl.cnf.rpmnew'
            ),
            reporting.Severity(reporting.Severity.MEDIUM),
            reporting.Groups([
                    reporting.Groups.SECURITY,
                    reporting.Groups.NETWORK,
                    reporting.Groups.SERVICES
            ]),
            reporting.Groups([
                reporting.Groups.POST
            ]),
            reporting.RelatedResource('package', 'openssl'),
            reporting.RelatedResource('file', '/etc/pki/tls/openssl.cnf')
        ])
