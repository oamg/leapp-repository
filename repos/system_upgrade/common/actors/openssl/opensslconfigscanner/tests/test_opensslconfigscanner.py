import pytest

from leapp.libraries.actor.readconf import parse_config, produce_config, strip_whitespace_and_comments
from leapp.models import OpenSslConfig, OpenSslConfigBlock, OpenSslConfigPair

testdata = (
    ('key = value', 'key = value'),  # normal formatting
    ('  key = value    ', 'key = value'),  # trailing and leading whitespace
    ('  key   =   value    ', 'key   =   value'),  # whitespace in between is kept
    ('[ section ]', '[ section ]'),  # normal section formatting
    ('    [ section ]    ', '[ section ]'),  # trailing and leading whitespace
    ('[    section    ]', '[    section    ]'),  # whitespace in braces is kept
    ('# comment', ''),  # only comment
    ('    # comment   ', ''),  # only comment with whitespace
    ('key = value# comment', 'key = value'),  # key value with comment
    ('key = value     # comment', 'key = value'),  # key value with comment and more whitespace
    ('[ section ]# comment', '[ section ]'),  # the section with comment
    ('[ section ]     # comment', '[ section ]'),  # the section with comment and more whitespace
)


@pytest.mark.parametrize('line,expected_result', testdata)
def test_strip_whitespace_and_comments(line, expected_result):
    result = strip_whitespace_and_comments(line)
    assert result == expected_result


def test_parse_config():
    config = [
        "# comment from file",
        "",  # empty line
        "   ",  # whitespace line
        "HOME                    = .",  # ignored before the start of block
        "openssl_conf = default_modules",  # the start key
        "# key = value in comment",  # ignored
        "HOME                    = .",  # ignored again
        "[ default_modules ]",  # first block
        "ssl_conf = ssl_module",
        "[ ssl_module ]",
        "system_default = crypto_policy",
        "[ crypto_policy ]",
        "# key = value in comment",  # ignored
        ".include = /etc/crypto-policies/back-ends/opensslcnf.config",
    ]

    output = parse_config(config)
    assert isinstance(output, OpenSslConfig)
    assert output.openssl_conf == "default_modules"
    assert len(output.blocks) == 3
    assert output.blocks[0].name == "default_modules"
    assert len(output.blocks[0].pairs) == 1
    assert output.blocks[0].pairs[0].key == "ssl_conf"
    assert output.blocks[0].pairs[0].value == "ssl_module"
    assert output.blocks[1].name == "ssl_module"
    assert len(output.blocks[1].pairs) == 1
    assert output.blocks[1].pairs[0].key == "system_default"
    assert output.blocks[1].pairs[0].value == "crypto_policy"
    assert output.blocks[2].name == "crypto_policy"
    assert len(output.blocks[2].pairs) == 1
    assert output.blocks[2].pairs[0].key == ".include"
    assert output.blocks[2].pairs[0].value == "/etc/crypto-policies/back-ends/opensslcnf.config"


def test_parse_config_empty():
    output = parse_config([])
    assert isinstance(output, OpenSslConfig)
    assert not output.openssl_conf
    assert len(output.blocks) == 0


def test_parse_config_bare_include():
    config = [
        "[ crypto_policy ]",
        ".include    /etc/crypto-policies/back-ends/opensslcnf.config",
    ]
    output = parse_config(config)
    assert isinstance(output, OpenSslConfig)
    assert not output.openssl_conf
    assert len(output.blocks) == 1
    assert output.blocks[0].name == "crypto_policy"
    assert len(output.blocks[0].pairs) == 1
    assert output.blocks[0].pairs[0].key == ".include"
    assert output.blocks[0].pairs[0].value == "/etc/crypto-policies/back-ends/opensslcnf.config"


def test_produce_config():
    output = []

    def fake_producer(*args):
        output.extend(args)

    config = OpenSslConfig(
        openssl_conf="default_modules",
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
            )
        ]
    )

    produce_config(fake_producer, config)
    assert len(output) == 1
    cfg = output[0]
    assert cfg.openssl_conf == "default_modules"
    assert len(cfg.blocks) == 3
    assert cfg.blocks[0].name == "default_modules"
    assert len(cfg.blocks[0].pairs) == 1
    assert cfg.blocks[0].pairs[0].key == "ssl_conf"
    assert cfg.blocks[0].pairs[0].value == "ssl_module"
    assert cfg.blocks[1].name == "ssl_module"
    assert len(cfg.blocks[1].pairs) == 1
    assert cfg.blocks[1].pairs[0].key == "system_default"
    assert cfg.blocks[1].pairs[0].value == "crypto_policy"
    assert cfg.blocks[2].name == "crypto_policy"
    assert len(cfg.blocks[2].pairs) == 1
    assert cfg.blocks[2].pairs[0].key == ".include"
    assert cfg.blocks[2].pairs[0].value == "/etc/crypto-policies/back-ends/opensslcnf.config"


def test_actor_execution(current_actor_context):
    current_actor_context.run()
    assert current_actor_context.consume(OpenSslConfig)
