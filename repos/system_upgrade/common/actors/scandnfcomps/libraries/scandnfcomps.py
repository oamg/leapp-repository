import warnings

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.dnflibs import create_dnf_base, DNFRepoError
from leapp.libraries.stdlib import api
from leapp.models import DNFEnvironment, DNFGroup, InstalledDNFComps

try:
    import dnf
except ImportError:
    # NOTE(pstodulk): To stay consistent with other DNF related actors, but
    # I guess we can get rid of it nowadays.
    dnf = None
    warnings.warn('Could not import the `dnf` python module.', ImportWarning)


def _get_installed_groups(base):
    """
    Query installed DNF comps groups via the DNF base object.

    Iterates over all available comps groups and filters to those recorded
    as installed in the DNF history.

    :param base: Initialized dnf.Base object with filled sack
    :type base: dnf.Base
    :returns: List of DNFGroup model instances sorted by group id
    :rtype: List[DNFGroup]
    """
    groups = []
    for grp in base.comps.groups_iter():
        if not base.history.group.get(grp.id):
            # not installed
            continue
        groups.append(DNFGroup(
            id=grp.id,
            name=grp.ui_name,
        ))
    return sorted(groups, key=lambda x: x.id)


def _get_installed_environments(base):
    """
    Query installed DNF comps environments via the DNF base object.

    Iterates over all available comps environments and filters to those
    recorded as installed in the DNF history.

    :param base: Initialized dnf.Base object with filled sack
    :type base: dnf.Base
    :returns: List of DNFEnvironment model instances sorted by environment id
    :rtype: List[DNFEnvironment]
    """
    environments = []
    for env in base.comps.environments_iter():
        if not base.history.env.get(env.id):
            continue
        environments.append(DNFEnvironment(
            id=env.id,
            name=env.ui_name,
        ))
    return sorted(environments, key=lambda x: x.id)


def process():
    """
    Scan installed DNF comps and produce InstalledDNFComps message.

    .. seealso::
        :func:`create_dnf_base` for exceptions raised when creating dnf.Base
    """
    if not dnf:
        api.current_logger().debug('DNF is not available, skipping DNF comps scan.')
        return

    try:
        base = create_dnf_base()
    except DNFRepoError as e:
        e.details['details'] = e.message
        raise StopActorExecutionError(
            message='Cannot obtain information about DNF Groups and Environments',
            details=e.details
        )

    api.produce(InstalledDNFComps(
        environments=_get_installed_environments(base),
        groups=_get_installed_groups(base),
    ))
