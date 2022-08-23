from leapp.libraries.common.tcpwrappersutils import config_applies_to_daemon


def config_affects_daemons(tcp_wrappers_facts, packages_list, daemons):
    """
    Check whether some of the daemons is installed and affected by existing
    configuration of tcp_wrappers based on the.

    :param tcp_wrappers_facts: Facts provided by the TcpWrappersFacts
    :param packages_list: List of packages provided by InstalledRedHatSignedRPM
    :param daemons: List of packages and keywords affecting daemons in this format:
                    [{"package-name", ["daemon1", "daemon2", ...], ...}]
    """
    found_packages = set()

    for (package, keywords) in daemons:
        # We do not care for particular daemon if the providing package is not installed
        if package not in packages_list:
            continue

        # Every package can have several daemons or daemons reacting to several keywords
        for daemon in keywords:
            # Is this daemon/keyword affected by the current configuration?
            if not config_applies_to_daemon(tcp_wrappers_facts, daemon):
                continue

            # We do not report particular daemons, but just the high-level list of packages
            found_packages.add(package)

    return found_packages
