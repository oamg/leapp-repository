"""
DNF-related libraries for the upgrade process.

This package consolidates DNF functionality previously scattered across:
- leapp.libraries.common.dnfconfig -> dnflibs.dnfconfig
- leapp.libraries.common.dnfplugin -> dnflibs.dnfplugin
- leapp.libraries.common.module -> dnflibs.dnfmodule
"""

import warnings

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config.version import get_source_major_version

try:
    import dnf
except ImportError:
    dnf = None
    warnings.warn('Could not import the `dnf` python module.', ImportWarning)


class DNFError(StopActorExecutionError):
    """
    Generic exception inherited by all DNF errors raised in dnflibs libraries.
    """


class DNFRepoError(DNFError):
    """
    Used when DNF fails to load repositories.
    """


def create_dnf_base():
    """
    Create properly initialized dnf.Base with filled sack.

    The proper initialisation of dnf.Base object is non-trivial and order of
    operations matters - we made plenty of mistakes already before the function
    got to this state, covering various setups and systems. So use it instead
    of trying to do so manually.

    :returns: Initialized dnf.Base object with filled sack
    :rtype: dnf.Base
    :raises DNFRepoError: When a repository cannot be loaded
    """
    # The DNF command reads /etc/dnf/vars/releasever, but the DNF library does not. It parses redhat-release
    # package to retrieve system's major version which it then uses as $releasever. However, some systems might
    # have repositories only for the exact system version (including the minor number). In a case when
    # /etc/dnf/vars/releasever is present, read its contents so that we can access repositores on such systems.
    conf = dnf.conf.Conf()

    # preload releasever from what we know, this will be our fallback
    conf.substitutions['releasever'] = get_source_major_version()

    # load all substitutions from etc
    conf.substitutions.update_from_etc('/')

    base = dnf.Base(conf=conf)
    base.conf.read()
    base.init_plugins()
    base.read_all_repos()

    # configure plugins after the repositories are loaded
    # e.g. the amazon-id plugin requires loaded repositories
    # for the proper configuration.
    base.configure_plugins()

    try:
        base.fill_sack()
    except dnf.exceptions.RepoError as e:
        err_msg = str(e)
        repoid = err_msg.split('repo:')[-1].strip() if 'repo:' in err_msg else 'unknown repo'
        repoid = repoid.strip('"').strip("'").replace('\\"', '')
        raise DNFRepoError(
            message='DNF failed to load repositories: {}'.format(str(e)),
            details={
                'hint': 'Ensure the {} repository definition is correct or remove it '
                        'if the repository is not needed anymore.'.format(repoid)
            }
        )

    return base
