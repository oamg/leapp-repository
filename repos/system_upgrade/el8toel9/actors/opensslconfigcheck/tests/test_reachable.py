from leapp.libraries.actor.opensslconfigcheck import (
    _find_duplicates,
    _find_pair,
    _key_equal,
    _normalize_key,
    _openssl_duplicate_keys_in,
    _openssl_find_block,
    _openssl_reachable_block,
    _openssl_reachable_block_root,
    _openssl_reachable_key,
    _openssl_reachable_path
)
from leapp.models import OpenSslConfig, OpenSslConfigBlock, OpenSslConfigPair


def _setup_config():
    return OpenSslConfig(
        openssl_conf="default_modules",
        blocks=[
            OpenSslConfigBlock(
                name="default_modules",
                pairs=[
                    OpenSslConfigPair(
                        key="ssl_conf",
                        value="ssl_module",
                    )
                ]
            ),
            OpenSslConfigBlock(
                name="ssl_module",
                pairs=[
                    OpenSslConfigPair(
                        key="system_default",
                        value="crypto_policy",
                    )
                ]
            ),
            OpenSslConfigBlock(
                name="crypto_policy",
                pairs=[
                    OpenSslConfigPair(
                        key=".include",
                        value="/etc/crypto-policies/back-ends/opensslcnf.config",
                    )
                ]
            ),
            OpenSslConfigBlock(
                name="tsa",
                pairs=[
                    OpenSslConfigPair(
                        key="1.default_tsa",
                        value="tsa_config1",
                    ),
                    OpenSslConfigPair(
                        key="2.default_tsa",
                        value="tsa_config2",
                    )
                ]
            ),
            OpenSslConfigBlock(
                name="ca",
                pairs=[
                    OpenSslConfigPair(
                        key="default_ca",
                        value="CA_default",
                    ),
                ]
            ),
            OpenSslConfigBlock(
                name="CA_default",
                pairs=[
                    OpenSslConfigPair(
                        key="x509_extensions",
                        value="usr_cert",
                    ),
                ]
            ),
            OpenSslConfigBlock(
                name="usr_cert",
                pairs=[
                    OpenSslConfigPair(
                        key="subjectKeyIdentifier",
                        value="hash",
                    ),
                    OpenSslConfigPair(
                        key="basicConstraints",
                        value="critical,CA:true",
                    ),
                    OpenSslConfigPair(
                        key="keyUsage",
                        value="nonRepudiation, digitalSignature, keyEncipherment",
                    ),
                    OpenSslConfigPair(
                        key="subjectAltName",
                        value="email:copy",
                    ),
                    OpenSslConfigPair(
                        key="subjectAltName",
                        value="email:move",
                    ),  # yay, duplicate
                ]
            ),
            OpenSslConfigBlock(
                name="req",
                pairs=[
                    OpenSslConfigPair(
                        key="default_bits",
                        value="2048",
                    ),
                    OpenSslConfigPair(
                        key="default_md",
                        value="sha256",
                    ),
                    OpenSslConfigPair(
                        key="x509_extensions",
                        value="v3_ca",
                    ),
                ]
            ),
            OpenSslConfigBlock(
                name="v3_ca",
                pairs=[
                    OpenSslConfigPair(
                        key="subjectKeyIdentifier",
                        value="hash",
                    ),
                    OpenSslConfigPair(
                        key="basicConstraints",
                        value="critical,CA:true",
                    ),
                    OpenSslConfigPair(
                        key="keyUsage",
                        value="cRLSign, keyCertSign",
                    ),
                    OpenSslConfigPair(
                        key="keyUsage",
                        value="cRLSign",
                    ),  # yay, duplicate
                    OpenSslConfigPair(
                        key="keyUsage",
                        value="keyCertSign",
                    ),  # yay, duplicate
                ]
            ),
        ]
    )


def test_normalize_key():
    assert _normalize_key("default_tsa") == "default_tsa"

    # TODO this is questionable, but probably ok
    assert _normalize_key(".include") == "include"

    assert _normalize_key("DTLS.MaxProtocol") == "MaxProtocol"

    assert _normalize_key("DTLS.TLS.MaxProtocol") == "TLS.MaxProtocol"


def test_key_equal():
    pair = OpenSslConfigPair(key="default_tsa", value="tsa_config1")
    assert _key_equal(pair, "default_tsa")

    pair = OpenSslConfigPair(key="default_tsa", value="tsa_config1")
    assert not _key_equal(pair, "tsa")

    pair = OpenSslConfigPair(key=".include", value="/some/path")
    assert _key_equal(pair, ".include")

    # TODO this is questionable, but probably ok
    pair = OpenSslConfigPair(key=".include", value="/some/path")
    assert _key_equal(pair, "include")

    pair = OpenSslConfigPair(key="DTLS.MaxProtocol", value="DTLSv1.2")
    assert _key_equal(pair, "MaxProtocol")

    pair = OpenSslConfigPair(key="DTLS.TLS.MaxProtocol", value="DTLSv1.2")
    assert not _key_equal(pair, "MaxProtocol")


def test_find():
    config = _setup_config()

    result = _openssl_find_block(config, 'default_modules')
    assert result.name == 'default_modules'
    pair = _find_pair(result, 'ssl_conf')
    assert pair.key == 'ssl_conf'
    assert pair.value == 'ssl_module'

    result = _openssl_find_block(config, 'ssl_module')
    assert result.name == 'ssl_module'
    pair = _find_pair(result, 'system_default')
    assert pair.key == 'system_default'
    assert pair.value == 'crypto_policy'

    result = _openssl_find_block(config, 'crypto_policy')
    assert result.name == 'crypto_policy'
    pair = _find_pair(result, '.include')
    assert pair.key == '.include'
    assert pair.value == '/etc/crypto-policies/back-ends/opensslcnf.config'

    assert _find_pair(result, 'nonexisting') is None

    assert _openssl_find_block(config, 'nonexisting') is None

    # duplicates
    b = _openssl_find_block(config, "tsa")
    assert b
    p = _find_pair(b, "default_tsa")
    assert p.key == "2.default_tsa"
    assert p.value == "tsa_config2"


def test_reachable_block():
    config = _setup_config()

    assert _openssl_reachable_block_root(config, "default_modules")

    assert _openssl_reachable_block_root(config, "ssl_module")

    assert _openssl_reachable_block_root(config, "crypto_policy")

    assert not _openssl_reachable_block_root(config, "crypto_policy", 1)

    assert not _openssl_reachable_block_root(config, "tsa")

    # searching from arbitrary block
    assert _openssl_reachable_block(config, "tsa", "tsa_config1")

    # non-existent start key
    assert not _openssl_reachable_block(config, "ecdsa", "crypto_policy")


def test_reachable_path():
    config = _setup_config()

    assert _openssl_reachable_path(config,
                                   ("default_modules", "ssl_conf", "ssl_module", "system_default",
                                    "crypto_policy", ".include"),
                                   "/etc/crypto-policies/back-ends/opensslcnf.config")

    assert _openssl_reachable_path(config,
                                   ("ssl_module", "system_default"),
                                   "crypto_policy")

    # missing key in the path
    assert not _openssl_reachable_path(config,
                                       ("ssl_module", "system_default", "crypto_policy"),
                                       "crypto_policy")

    # non continuous path/wrong value in path
    assert not _openssl_reachable_path(config,
                                       ("ssl_module", "tsa"),
                                       "tsa_config1")

    # wrong value
    assert not _openssl_reachable_path(config,
                                       ("ssl_module", "system_default"),
                                       ".include")

    # not reachable from the root
    assert not _openssl_reachable_path(config,
                                       ("tsa", "default_tsa"),
                                       "tsa_config1")

    # any value
    assert _openssl_reachable_path(config, ("ssl_module", "system_default"))
    assert not _openssl_reachable_path(config, ("ssl_module", "tsa"))


def test_reachable_key():
    config = _setup_config()

    assert _openssl_reachable_key(config, "system_default")
    assert _openssl_reachable_key(config, "system_default", "crypto_policy")
    assert not _openssl_reachable_key(config, "tsa")
    assert not _openssl_reachable_key(config, "default_tsa", "tsa_config2")


def test_find_duplicates():
    config = _setup_config()

    d = _find_duplicates(config, "non-existent")
    assert len(d) == 0

    d = _find_duplicates(config, "default_modules")
    assert len(d) == 0

    d = _find_duplicates(config, "tsa")
    assert len(d) == 1
    assert d[0] == 'default_tsa'

    d = _find_duplicates(config, "v3_ca")
    assert len(d) == 1
    assert d[0] == 'keyUsage'

    d = _find_duplicates(config, "usr_cert")
    assert len(d) == 1
    assert d[0] == 'subjectAltName'


def test_duplicate_keys_in():
    config = _setup_config()

    d = _openssl_duplicate_keys_in(config, "x509_extensions")
    assert len(d) == 2
    assert 'keyUsage' in d
    assert 'subjectAltName' in d
