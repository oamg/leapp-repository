import os
from shutil import copy

from leapp.libraries.stdlib import api
from leapp.models import CupsChangedFeatures

CUPSD_CONF = '/etc/cups/cupsd.conf'
CUPSFILES_CONF = '/etc/cups/cups-files.conf'
"""
CUPS configuration files
"""


class FileOperations(object):
    def readlines(self, path):
        if os.path.exists(path):
            with open(path, 'r') as f:
                return f.readlines()
        else:
            raise IOError('Error when reading file {} - file '
                          'does not exist.'.format(path))

    def write(self, path, mode, content):
        if isinstance(content, list):
            content = ''.join(content)
        with open(path, mode) as f:
            f.write(content)

    def copy_to_ssl(self, oldpath):
        copy(oldpath, '/etc/cups/ssl')


def migrate_digest(op):
    """
    Replaces Digest/BasicDigest for Basic

    :param obj op: file operations object
    """
    try:
        lines = op.readlines(CUPSD_CONF)
    except IOError as error:
        raise IOError(error)

    for line in lines:
        for directive in ['AuthType', 'DefaultAuthType']:
            if line.lstrip().startswith(directive):
                auth_line_value = line.lstrip().lstrip(directive).lstrip()
                for value in ['Digest', 'BasicDigest']:
                    if auth_line_value.startswith(value):
                        lines[lines.index(line)] = '{} Basic\n'.format(directive)

    op.write(CUPSD_CONF, 'w', lines)


def migrate_include(include_files, op):
    """
    Concatenates configuration files and remove lines
    with 'Include' directive

    :param list include_files: list of files which contents will be
    concatenated
    :param obj op: file operations object
    """
    error_list = []
    lines = []
    content = []

    for f in include_files:
        try:
            content = op.readlines(f)
            if f != CUPSD_CONF:
                content = ['\n# added by Leapp\n'] + content
            lines += content
        except IOError as error:
            error_list.append('Include directive: {}'.format(error))

    if error_list:
        return error_list

    for line in lines:
        if line.lstrip().startswith('Include'):
            lines[lines.index(line)] = ''

    op.write(CUPSD_CONF, 'w', lines)

    return None


def move_directives(directives, op):
    """
    Moves the directives from cupsd.conf to cups-files.conf

    :param list directives: list of wanted directives
    :param obj op: file operations object
    """
    try:
        cupsd_lines = op.readlines(CUPSD_CONF)
    except IOError as error:
        raise IOError(error)

    lines_to_move = []
    for line in cupsd_lines:
        for name in directives:
            if line.lstrip().startswith(name):
                lines_to_move.append(line)
                cupsd_lines[cupsd_lines.index(line)] = ''

    op.write(CUPSD_CONF, 'w', cupsd_lines)

    if lines_to_move:
        op.write(CUPSFILES_CONF, 'a',
                 '\n# added by Leapp\n{}'.format(''.join(lines_to_move)))


def migrate_certkey(op):
    """
    Copies the key and the certificate to /etc/cups/ssl if both
    are in different dirs, or sets ServerKeychain value to the dir
    where the key and the certificate are. Removes old directives

    :param list directives: list of wanted directives
    :param obj op: file operations object
    """
    try:
        lines = op.readlines(CUPSFILES_CONF)
    except IOError as error:
        raise IOError(error)

    certkey_values = []

    for line in lines:
        for name in ['ServerKey', 'ServerCertificate']:
            if line.lstrip().startswith(name):
                value = line.split()[1]
                if value.startswith('ssl'):
                    value = os.path.join('/etc/cups', value)
                certkey_values.append(value)
                lines[lines.index(line)] = ''

    op.write(CUPSFILES_CONF, 'w', lines)

    # we need to decide whether we copy the files to /etc/cups/ssl
    # or set ServerKeychain to non-default directory or do nothing
    if all(os.path.dirname(val) == '/etc/cups/ssl' for val in certkey_values):
        return

    # Check that all files are inside the same directory
    if len(set([os.path.dirname(certkey) for certkey in certkey_values])) == 1:
        path = os.path.dirname(certkey_values[0])
        op.write(CUPSFILES_CONF, 'a',
                 '\n# added by Leapp\nServerKeychain {}\n'.format(path))
    else:
        for value in certkey_values:
            if not os.path.dirname(value) == '/etc/cups/ssl':
                op.copy_to_ssl(value)


def _get_facts(model):
    """
    Consumes input data model

    :param class model: name of model which we consume
    """
    return next(api.consume(model), None)


def migrate_configuration(error_log=api.current_logger().error,
                          debug_log=api.current_logger().debug,
                          op=FileOperations(),
                          consume_function=_get_facts):
    """
    Migrate CUPS configuration based on gathered facts

    :param func error_log: sends error messages
    :param func debug_log: sends debug messages
    :param obj op: IO operations
    :param func consume_function: receives data object from a model
    """

    facts = consume_function(CupsChangedFeatures)
    error_list = []

    if not facts:
        return

    if facts.include:
        debug_log('Migrating CUPS configuration - Include directives.')
        include_errors = []

        include_errors = migrate_include(facts.include_files, op)
        if include_errors:
            error_list += include_errors

    if facts.digest:
        debug_log('Migrating CUPS configuration - BasicDigest/Digest directives.')

        try:
            migrate_digest(op)
        except IOError as error:
            error_list.append('Digest/BasicDigest values: {}'.format(error))

    if facts.env:
        debug_log('Migrating CUPS configuration - PassEnv/SetEnv directives.')

        try:
            move_directives(['PassEnv', 'SetEnv'],
                            op)
        except IOError as error:
            error_list.append('PassEnv/SetEnv directives: {}'.format(error))

    if facts.certkey:
        debug_log('Migrating CUPS configuration - '
                  'ServerKey/ServerCertificate directive.')

        try:
            migrate_certkey(op)
        except IOError as error:
            error_list.append('ServerKey/ServerCertificate directives: {}'.format(error))

    if facts.printcap:
        debug_log('Migrating CUPS configuration - PrintcapFormat directive.')

        try:
            move_directives(['PrintcapFormat'],
                            op)
        except IOError as error:
            error_list.append('PrintcapFormat directive: {}'.format(error))

    if error_list:
        error_log('Following errors happened during CUPS migration:'
                  + ''.join(['\n   - {}'.format(err) for err in error_list]))
