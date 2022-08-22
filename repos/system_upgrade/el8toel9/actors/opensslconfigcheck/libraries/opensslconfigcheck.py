from leapp import reporting
from leapp.libraries.stdlib import api


def _normalize_key(key):
    """
    Strip the part of the key before the first dot
    """
    s = key.split(".", 1)
    if len(s) == 2:
        return s[1]
    return key


def _key_equal(pair, key):
    """
    Check the keys are equal in OpenSSL configuration semantics

    The OpenSSL semantics ignores everything before the first dot to allow specifying
    something like following, where the first line would be otherwise normally ignored

        TLS.MaxProtocol = TLSv1.3
        DTLS.MaxProtocol = DTLSv1.2
    """
    if pair.key == key:
        return True
    return _normalize_key(pair.key) == key


def _find_pair(block, key):
    """
    Find key-value pair in the given configuration block

    In the given configuration block (OpenSslConfigBlock) find a key-value with a given key.
    If multiple values match, only the last one is returned.
    """
    res = None
    for pair in block.pairs:
        if _key_equal(pair, key):
            res = pair

    return res


def _openssl_find_block(config, name):
    """
    In the given configuration file (OpenSslConfig) find a block with a given name
    """
    for block in config.blocks:
        if block.name == name:
            return block

    return None


def _openssl_reachable_block(config, start_name, end_name, limit=10):
    """
    Check if the end_name is reachable from the start_name in given config

    This searches path between one block name and some other block name in a chain
    like (the names in square braces are block names, the other keys pointing to another
    block in the chain)
    [default_modules] -> ssl_conf -> [ssl_module] -> system_default -> [crypto_policy]
    using simple recursion. The end block name is not checked for presence so it can
    be just value.
    """
    if limit <= 0:
        api.current_logger().debug("Recursion limit reached while searching for {}."
                                   .format(end_name))
        return False

    if start_name == end_name:
        return True

    start = _openssl_find_block(config, start_name)
    if not start:
        api.current_logger().debug("Starting block {} not found in current configuration"
                                   .format(start_name))
        return False

    for pair in start.pairs:
        if pair.value == end_name:
            return True
        block = _openssl_find_block(config, pair.value)
        if block and _openssl_reachable_block(config, block.name, end_name, limit - 1):
            return True

    return False


def _openssl_reachable_block_root(config, end_name, limit=10):
    """
    Check if the given block is reachable from the root block given in the config.
    """
    return _openssl_reachable_block(config, config.openssl_conf, end_name, limit)


def _openssl_reachable_key(config, key, value=None):
    """
    Check if the key=value pair is reachable from the root block.

    If no value is specified, any value assigned to the given key is matched.
    """
    for block in config.blocks:
        for pair in block.pairs:
            if _key_equal(pair, key) and (value is None or pair.value == value):
                api.current_logger().debug("The key {} found in block {}"
                                           .format(key, block.name))
                if _openssl_reachable_block_root(config, block.name):
                    api.current_logger().debug("The block {} is reachable from the start key {}"
                                               .format(block.name, config.openssl_conf))
                    return True

    api.current_logger().debug("The key {} not found".format(key))
    return False


# pylint: disable=too-many-return-statements -- could not simplify more
def _openssl_reachable_path(config, path, value=None):
    """
    Check if the given path is reachable in OpenSSL configuration

    The path is list where to search for a value. It is a list of keys starting
    with a section of a known name followed by key to search for in that section
    and then another section, which is assigned to that key.

    If no value is specified, any value assigned to the given key is matched.
    """
    path_iterator = iter(path)
    block_name = next(path_iterator)
    if not _openssl_reachable_block_root(config, block_name):
        api.current_logger().debug("The block {} not reachable from the start key {}"
                                   .format(block_name, config.openssl_conf))
        return False

    while block_name and block_name != value:
        # Find in the block by name
        block = _openssl_find_block(config, block_name)
        if not block:
            api.current_logger().debug("Block {} not found in current configuration"
                                       .format(block_name))
            return False

        try:
            key = next(path_iterator)
        except StopIteration:
            api.current_logger().debug("Missing key in the path")
            return False

        # Find the pair in block
        pair = _find_pair(block, key)
        if not pair:
            api.current_logger().debug("Key {} not found in block {}".format(key, block_name))
            return False

        try:
            block_name = next(path_iterator)
        except StopIteration:
            # if there are no other parts in the path and the value is the one we look for, stop
            if pair.value == value or value is None:
                api.current_logger().debug("Found reachable value {}".format(pair.value))
                return True

        # otherwise make sure it is the expected one
        if pair.value != block_name:
            return False

    api.current_logger().debug("Value {} not reachable in current configuration".format(value))
    return False


def _find_duplicates(config, block_name):
    """
    Finds duplicate keys in given block name
    """
    block = _openssl_find_block(config, block_name)
    if not block:
        api.current_logger().debug("Did not find a block {} when searching for duplicates"
                                   .format(block_name))
        return []

    duplicates = []
    # not most effective
    for p in block.pairs:
        for p2 in block.pairs:
            key = _normalize_key(p.key)
            if p != p2 and key == _normalize_key(p2.key) and key not in duplicates:
                duplicates.append(key)

    return duplicates


def _openssl_duplicate_keys_in(config, key):
    """
    Search for duplicate keys in block named "key"

    Used for searching for duplicate extensions. The given key can be defined in different
    blocks and references a block where we search for duplicate keys with the openssl specific
    name handling (ignoring content before the dot).
    """
    duplicates = []

    # first find all the keys in all the blocks with the given name
    for block in config.blocks:
        for pair in block.pairs:
            if _key_equal(pair, key):
                duplicates += _find_duplicates(config, pair.value)

    return duplicates


resources = [
    reporting.RelatedResource('package', 'openssl'),
    reporting.RelatedResource('file', '/etc/pki/tls/openssl.cnf')
]


def check_crypto_policies(config):
    """
    Check the presence of the crypto policies include

    The default openssl.cnf provides include of dynamic crypto policies to keep
    applications using OpenSSL in sync with the rest of the OS. Not having this
    directive in the configuration file is not recommended.
    """
    if not _openssl_reachable_path(config,
                                   path=("default_modules", "ssl_conf", "ssl_module",
                                         "system_default", "crypto_policy", ".include"),
                                   value="/etc/crypto-policies/back-ends/opensslcnf.config"):
        reporting.create_report([
            reporting.Title('The OpenSSL configuration is missing the crypto policies integration'),
            reporting.Summary(
                'The OpenSSL configuration file `/etc/pki/tls/openssl.cnf` does not contain the '
                'directive to include the system-wide crypto policies. This is not recommended '
                'by Red Hat and can lead to decreasing overall system security and inconsistent '
                'behavior between applications. If you need to adjust the crypto policies to your '
                'needs, it is recommended to use custom crypto policies.'
            ),
            reporting.Severity(reporting.Severity.MEDIUM),
            reporting.Groups([
                    reporting.Groups.AUTHENTICATION,
                    reporting.Groups.SECURITY,
                    reporting.Groups.NETWORK,
                    reporting.Groups.SERVICES
            ]),
            reporting.RelatedResource('package', 'crypto-policies'),
        ] + resources)


def check_min_max_protocol(config):
    """
    Check for the MinProtocol and MaxProtocol options

    These options changed their meaning in openssl.cnf so better warn the user
    """
    if _openssl_reachable_key(config, "MinProtocol") or _openssl_reachable_key(config, "MaxProtocol"):
        reporting.create_report([
            reporting.Title('The meaning of MinProtocol and MaxProtocol in openssl.cnf changed'),
            reporting.Summary(
                'The OpenSSL configuration file `/etc/pki/tls/openssl.cnf` contain the '
                'directive MinProtocol or MaxProtocol, which was previously applied to both '
                'TLS and DTLS versions. This is no longer case and if you want to limit both '
                'protocols, you need to add another option, for example for '
                '`MinProtocol TLSv1.2` add the following line `DTLS.MinProtocol = DTLSv1.2`.'
            ),
            reporting.Severity(reporting.Severity.MEDIUM),
            reporting.Groups([
                    reporting.Groups.SECURITY,
                    reporting.Groups.NETWORK,
                    reporting.Groups.SERVICES
            ]),
        ] + resources)


def check_duplicate_extensions(config):
    dup = _openssl_duplicate_keys_in(config, "x509_extensions")
    if dup:
        reporting.create_report([
            reporting.Title('There are duplicate x509 extensions defined in openssl.cnf'),
            reporting.Summary(
                'The OpenSSL configuration file `/etc/pki/tls/openssl.cnf` contains the '
                'following duplicate X509 extensions: {}. With OpenSSL 3.0 only the last defined '
                'will get used. Please, review the configuration file and remove duplicate '
                'extensions to silence this warning.'.format(', '.join(dup))
            ),
            reporting.Severity(reporting.Severity.LOW),
            reporting.Groups([
                    reporting.Groups.SECURITY,
                    reporting.Groups.NETWORK,
                    reporting.Groups.SERVICES
            ]),
        ] + resources)


def check_default_modules(config):
    if config.openssl_conf != "default_modules" or not _openssl_find_block(config, "default_modules"):
        reporting.create_report([
            reporting.Title('Non-standard configuration of openssl.cnf'),
            reporting.Summary(
                'The OpenSSL configuration file `/etc/pki/tls/openssl.cnf` does not contain '
                'expected initialization so it can not be updated to support OpenSSL 3.0 '
                'with the new providers.'
            ),
            reporting.Remediation(
                'The openssl.cnf file needs to contain the following initialization: '
                '`openssl_conf = default_modules` and corresponding `[ default_modules] '
                'block. The `openssl_conf` now contains {} or the `[ default_modules ]` '
                'block is missing. '.format(config.openssl_conf)
            ),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([
                    reporting.Groups.SECURITY,
                    reporting.Groups.NETWORK,
                    reporting.Groups.SERVICES
            ]),
        ] + resources)
    else:
        reporting.create_report([
            reporting.Title('The OpenSSL configuration will be updated to support OpenSSL 3.0'),
            reporting.Summary(
                'The OpenSSL configuration file `/etc/pki/tls/openssl.cnf` will be updated '
                'to support OpenSSL 3.0 with the new providers. The following changes are '
                'going to be applied:\n'
                ' * Change the initialization:\n'
                '\n'
                ' - openssl_conf = default_modules\n'
                ' + openssl_conf = openssl_init\n'
                '\n'
                ' * Rename the default block and link the providers block:\n'
                '\n'
                ' - [default_modules]\n'
                ' + [openssl_init]\n'
                ' + providers = provider_sect\n'
                '\n'
                ' * Add the providers block:\n'
                '\n'
                ' + [provider_sect]\n'
                ' + default = default_sect\n'
                ' + ##legacy = legacy_sect\n'
                ' + \n'
                ' + [default_sect]\n'
                ' + activate = 1\n'
                ' + \n'
                ' + ##[legacy_sect]\n'
                ' + ##activate = 1\n'
            ),
            reporting.Severity(reporting.Severity.INFO),
            reporting.Groups([
                    reporting.Groups.SECURITY,
                    reporting.Groups.NETWORK,
                    reporting.Groups.SERVICES
            ]),
        ] + resources)
