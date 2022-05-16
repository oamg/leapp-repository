from leapp.models import OpenSslConfig, OpenSslConfigBlock, OpenSslConfigPair, Report


def test_actor_execution_empty(current_actor_context):
    current_actor_context.feed(
        OpenSslConfig(
            blocks=[],
            # modified=False, # default
        )
    )
    current_actor_context.run()
    assert not current_actor_context.consume(Report)


def test_actor_execution_empty_modified(current_actor_context):
    current_actor_context.feed(
        OpenSslConfig(
            blocks=[],
            modified=True,
        )
    )
    current_actor_context.run()
    r = current_actor_context.consume(Report)
    assert r
    assert 'missing the crypto policies integration' in r[0].report['title']


def test_actor_execution_default_modified(current_actor_context):
    current_actor_context.feed(
        OpenSslConfig(
            openssl_conf='default_modules',
            blocks=[
                OpenSslConfigBlock(
                    name="default_modules",
                    pairs=[
                        OpenSslConfigPair(
                            key="ssl_conf",
                            value="ssl_module"
                        )
                    ]
                ),
                OpenSslConfigBlock(
                    name="ssl_module",
                    pairs=[
                        OpenSslConfigPair(
                            key="system_default",
                            value="crypto_policy"
                        )
                    ]
                ),
                OpenSslConfigBlock(
                    name="crypto_policy",
                    pairs=[
                        OpenSslConfigPair(
                            key=".include",
                            value="/etc/crypto-policies/back-ends/opensslcnf.config"
                        )
                    ]
                ),
            ],
            modified=True,
        )
    )
    current_actor_context.run()
    r = current_actor_context.consume(Report)
    assert r
    assert 'The OpenSSL configuration will be updated to support OpenSSL 3.0' in r[0].report['title']


def test_actor_execution_minprotocol_modified(current_actor_context):
    current_actor_context.feed(
        OpenSslConfig(
            openssl_conf='default_modules',
            blocks=[
                OpenSslConfigBlock(
                    name="default_modules",
                    pairs=[
                        OpenSslConfigPair(
                            key="ssl_conf",
                            value="ssl_module"
                        )
                    ]
                ),
                OpenSslConfigBlock(
                    name="ssl_module",
                    pairs=[
                        OpenSslConfigPair(
                            key="system_default",
                            value="crypto_policy"
                        )
                    ]
                ),
                OpenSslConfigBlock(
                    name="crypto_policy",
                    pairs=[
                        OpenSslConfigPair(
                            key=".include",
                            value="/etc/crypto-policies/back-ends/opensslcnf.config"
                        )
                    ]
                ),
                OpenSslConfigBlock(
                    name="crypto_policy",
                    pairs=[
                        OpenSslConfigPair(
                            key="TLS.MinProtocol",
                            value="TLSv1.2"
                        ),
                    ]
                )
            ],
            modified=True,
        )
    )
    current_actor_context.run()
    r = current_actor_context.consume(Report)
    assert r
    assert 'MinProtocol and MaxProtocol' in r[0].report['title']
    assert 'The OpenSSL configuration will be updated to support OpenSSL 3.0' in r[1].report['title']


def test_actor_execution_duplicate_extensions_modified(current_actor_context):
    current_actor_context.feed(
        OpenSslConfig(
            openssl_conf='default_modules',
            blocks=[
                OpenSslConfigBlock(
                    name="default_modules",
                    pairs=[
                        OpenSslConfigPair(
                            key="ssl_conf",
                            value="ssl_module"
                        )
                    ]
                ),
                OpenSslConfigBlock(
                    name="ssl_module",
                    pairs=[
                        OpenSslConfigPair(
                            key="system_default",
                            value="crypto_policy"
                        )
                    ]
                ),
                OpenSslConfigBlock(
                    name="crypto_policy",
                    pairs=[
                        OpenSslConfigPair(
                            key=".include",
                            value="/etc/crypto-policies/back-ends/opensslcnf.config"
                        )
                    ]
                ),
                OpenSslConfigBlock(
                    name="req",
                    pairs=[
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
            ],
            modified=True,
        )
    )
    current_actor_context.run()
    r = current_actor_context.consume(Report)
    assert r
    assert 'duplicate x509 extensions' in r[0].report['title']
    assert 'keyUsage' in r[0].report['summary']
    assert 'The OpenSSL configuration will be updated to support OpenSSL 3.0' in r[1].report['title']
