from leapp.libraries.stdlib import api


def get_env(name, default=None):
    """Return Leapp environment variable value if matched by name."""
    for var in api.current_actor().configuration.leapp_env_vars:
        if var.name == name:
            return var.value
    return default


def get_all_envs():
    """Return all Leapp environment variables (both name and value)."""
    return api.current_actor().configuration.leapp_env_vars


def get_product_type(sys_type):
    """
    Get expected product type (ga/beta/htb) of the chosen sys type.

    By default, expected product type is 'ga'. It can be changed using these envars:
        LEAPP_DEVEL_SOURCE_PRODUCT_TYPE
        LEAPP_DEVEL_TARGET_PRODUCT_TYPE
    which can set the product type of chosen system (source/target) to one of
    valid product types: ga/beta/htb.

    Raise ValueError when specified sys_type or set product_type is invalid.

    :param sys_type: choose system for which to get the product type: 'source' or 'target'
    :type sys_type: str
    :return: 'ga' (default), 'htb', 'beta'
    :rtype: str
    """
    if sys_type == 'source':
        envar = 'LEAPP_DEVEL_SOURCE_PRODUCT_TYPE'
    elif sys_type == 'target':
        envar = 'LEAPP_DEVEL_TARGET_PRODUCT_TYPE'
    else:
        raise ValueError('Given invalid sys_type. Valid values: source/target')
    val = get_env(envar, '').lower()
    if not val:
        return 'ga'
    if val in ('beta', 'htb', 'ga'):
        return val
    raise ValueError('Invalid value in the {} envar. Possible values: ga/beta/htb.'.format(envar))
