import os
import re

from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, PostfixBdbConfiguration

DEFAULT_POSTFIX_PATHS = ['/etc/postfix']

# Map type used as a prefix: hash:/etc/aliases, proxy:hash:/path, ...
BDB_MAP_RE = re.compile(r'(?:^|[\s,=:])(hash|btree):', re.IGNORECASE)
# Compiled default on RHEL 9 is hash; an explicit setting of hash/btree is also BDB.
DEFAULT_DB_RE = re.compile(r'^\s*default_database_type\s*=\s*(hash|btree)\b', re.IGNORECASE)


def _iter_config_files(paths):
    """Yield Postfix *.cf files from the given files or directories."""
    for path in paths:
        if os.path.isdir(path):
            try:
                names = os.listdir(path)
            except OSError as err:
                api.current_logger().warning(
                    'Could not list Postfix configuration directory {}: {}'.format(path, err)
                )
                continue
            for name in sorted(names):
                if name.endswith('.cf'):
                    yield os.path.join(path, name)
        elif os.path.isfile(path):
            yield path


def _scan_file(path):
    """Return list of 'path: line' strings for Berkeley DB map settings."""
    occurrences = []
    try:
        with open(path) as conf_file:
            for line in conf_file:
                stripped = line.strip()
                if not stripped or stripped.startswith('#'):
                    continue
                if BDB_MAP_RE.search(stripped) or DEFAULT_DB_RE.search(stripped):
                    occurrences.append('{}: {}'.format(path, stripped))
    except OSError as err:
        api.current_logger().warning(
            'Could not read Postfix configuration file {}: {}'.format(path, err)
        )
    return occurrences


def scan_postfix_configuration(conf_paths=None, _context=api):
    """
    Scan Postfix configuration for Berkeley DB (hash/btree) lookup tables.

    :param conf_paths: Files or directories to scan. Defaults to /etc/postfix.
    :return: PostfixBdbConfiguration
    """
    postfix_present = has_package(DistributionSignedRPM, 'postfix', context=_context)
    if not postfix_present:
        return PostfixBdbConfiguration(postfix_present=False, bdb_occurrences=[])

    paths = DEFAULT_POSTFIX_PATHS if conf_paths is None else conf_paths
    occurrences = []
    for conf_file in _iter_config_files(paths):
        occurrences.extend(_scan_file(conf_file))

    return PostfixBdbConfiguration(
        postfix_present=True,
        bdb_occurrences=occurrences,
    )
