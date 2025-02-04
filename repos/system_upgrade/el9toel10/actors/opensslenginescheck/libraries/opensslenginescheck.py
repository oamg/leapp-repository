from leapp import reporting
from leapp.libraries.stdlib import api

FMT_LIST_SEPARATOR = '\n    - '
RESOURCES = [
    reporting.RelatedResource('package', 'openssl'),
    reporting.RelatedResource('file', '/etc/pki/tls/openssl.cnf')
]


def _formatted_list_output(input_list, sep=FMT_LIST_SEPARATOR):
    return ['{}{}'.format(sep, item) for item in input_list]


# NOTE: This is taken from the el8toel9 library in
# repos/system_upgrade/el8toel9/actors/opensslconfigcheck/libraries/opensslconfigcheck.py
def _normalize_key(key):
    """
    Strip the part of the key before the first dot
    """
    s = key.split('.', 1)
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


def check_openssl_engines(config):
    """
    Check there are no engines configured in openssl.cnf

    Report any detected openssl engines defined in /etc/pki/tls/openssl.cnf.
    """
    init_block = _openssl_find_block(config, config.openssl_conf)
    if config.openssl_conf != 'openssl_init' or not init_block:
        api.current_logger().warning(
            'Non standard configuration in /etc/pki/tls/openssl.cnf: missing "openssl_init" section.'
        )
        return

    engines_pair = _find_pair(init_block, 'engines')
    if not engines_pair:
        # No engines no problem
        return

    engines_block = _openssl_find_block(config, engines_pair.value)
    if not engines_block:
        # No engines no problem
        return

    enabled_engines = []
    # Iterate over engines directives -- they point to another block
    for engine in engines_block.pairs:
        name = engine.key
        engine_block = _openssl_find_block(config, engine.value)

        # the engine is defined by name, but does not have a corresponding block
        if not engine_block:
            api.current_logger().debug(
                'The engine {} does not have corresponding configuration block.'
                .format(name)
            )
            continue

        enabled_engines.append(name)

    if enabled_engines:
        reporting.create_report([
            reporting.Title('Detected enabled deprecated engines in openssl.cnf'),
            reporting.Summary(
                'OpenSSL engines are deprecated since OpenSSL version 3.0'
                ' and they are no longer supported nor available on the target'
                ' RHEL 10 system. Any applications depending on OpenSSL engines'
                ' might not work correctly on the target system and should be configured'
                ' to use OpenSSL providers instead.'
                ' The following OpenSSL engines are configured inside the /etc/pki/tls/openssl.cnf file:{}'
                .format(''.join(_formatted_list_output(enabled_engines)))
            ),
            reporting.Remediation(hint=(
                'After the upgrade configure your system and applications'
                ' to use OpenSSL providers instead of OpenSSL engines if needed.'
            )),
            reporting.Severity(reporting.Severity.MEDIUM),
            reporting.Groups([
                    reporting.Groups.NETWORK,
                    reporting.Groups.POST,
                    reporting.Groups.SECURITY,
                    reporting.Groups.SERVICES,
            ]),
        ] + RESOURCES)
