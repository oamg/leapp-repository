def mpath_file_locations(configs):
    """
    Returns the configured location of the bindings_file, wwids_file, and
    prkeys_file multipath files, handling cases where the location is set
    multiple times (the last set value is used) or not set at all (None is
    used).

    :param configs: The ordered list of all multipath config files data
    :type configs: List[MultipathConfig9to10]
    :return: The locations of bindings_file, wwids_file, and prkeys_file
    :rtype: Tuple[Optional[str], Optional[str], Optional[str]]

    """

    bindings_file = None
    wwids_file = None
    prkeys_file = None
    for conf in configs:
        bindings_file = conf.bindings_file or bindings_file
        wwids_file = conf.wwids_file or wwids_file
        prkeys_file = conf.prkeys_file or prkeys_file
    return (bindings_file, wwids_file, prkeys_file)
