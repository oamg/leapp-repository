import os


def is_ipa_client_configured():
    """
    Check if ipa-client is configured on the system

    :return: True if client is configured
    :rtype: bool
    """
    return all(
        (
            os.path.isfile("/etc/ipa/default.conf"),
            os.path.isfile("/var/lib/ipa-client/sysrestore/sysrestore.state"),
        )
    )


def is_ipa_server_configured():
    """
    Check if ipa-server is configured on the system

    :return: True if server is configured
    :rtype: bool
    """
    return all(
        (
            is_ipa_client_configured(),
            os.path.isfile("/var/lib/ipa/sysrestore/sysrestore.state"),
        )
    )
