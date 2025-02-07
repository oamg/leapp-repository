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
    assert not current_actor_context.consume(Report)


def test_actor_execution_default_modified(current_actor_context):
    current_actor_context.feed(
        OpenSslConfig(
            openssl_conf='openssl_init',
            blocks=[
                OpenSslConfigBlock(
                    name='openssl_init',
                    pairs=[
                        OpenSslConfigPair(
                            key='providers',
                            value='provider_sect'
                        ),
                        OpenSslConfigPair(
                            key='ssl_conf',
                            value='ssl_module'
                        ),
                        OpenSslConfigPair(
                            key='alg_section',
                            value='evp_properties'
                        )
                    ]
                ),
                OpenSslConfigBlock(
                    name='evp_properties',
                    pairs=[]
                ),
                OpenSslConfigBlock(
                    name='provider_sect',
                    pairs=[
                        OpenSslConfigPair(
                            key='default',
                            value='default_sect'
                        )
                    ]
                ),
                OpenSslConfigBlock(
                    name='default_sect',
                    pairs=[
                        OpenSslConfigPair(
                            key='activate',
                            value='1'
                        )
                    ]
                ),
                OpenSslConfigBlock(
                    name='ssl_module',
                    pairs=[
                        OpenSslConfigPair(
                            key='system_default',
                            value='crypto_policy'
                        )
                    ]
                ),
                OpenSslConfigBlock(
                    name='crypto_policy',
                    pairs=[
                        OpenSslConfigPair(
                            key='.include',
                            value='/etc/crypto-policies/back-ends/opensslcnf.config'
                        )
                    ]
                ),
            ],
            modified=True,
        )
    )
    current_actor_context.run()
    assert not current_actor_context.consume(Report)


def test_actor_execution_other_engine_modified(current_actor_context):
    # default, but removing contents unrelated for the checks
    current_actor_context.feed(
        OpenSslConfig(
            openssl_conf='openssl_init',
            blocks=[
                OpenSslConfigBlock(
                    name='openssl_init',
                    pairs=[
                        OpenSslConfigPair(
                            key='engines',
                            value='engines_sect'
                        )
                    ]
                ),
                OpenSslConfigBlock(
                    name='engines_sect',
                    pairs=[
                        OpenSslConfigPair(
                            key='acme',
                            value='acme_sect'
                        )
                    ]
                ),
                OpenSslConfigBlock(
                    name='acme_sect',
                    pairs=[
                        OpenSslConfigPair(
                            key='init',
                            value='0'
                        )
                    ]
                )
            ],
            modified=True,
        )
    )
    current_actor_context.run()
    report = current_actor_context.consume(Report)
    assert report
    assert 'Detected enabled deprecated engines in openssl.cnf' in report[0].report['title']
    assert 'acme' in report[0].report['summary']
