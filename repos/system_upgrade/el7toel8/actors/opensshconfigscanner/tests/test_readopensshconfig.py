from leapp.models import OpenSshConfig, OpenSshPermitRootLogin
from leapp.libraries.actor.readopensshconfig import parse_config, \
    produce_config, line_empty, parse_config_modification


def test_line_empty():
    assert line_empty("".strip()) is True
    assert line_empty("     ".strip()) is True
    assert line_empty("   # comment".strip()) is True
    assert line_empty("# comment".strip()) is True
    assert line_empty("option".strip()) is False
    assert line_empty("    option".strip()) is False


def test_parse_config():
    config = [
        "# comment from file",
        "",  # empty line
        "   ",  # whitespace line
        "permitrootlogin prohibit-password",
        "permittty yes",
        "useprivilegeseparation no",
        "protocol 2",
        "hostkey /etc/ssh/ssh_host_ecdsa_key",  # unrelated duplicate keys
        "hostkey /etc/ssh/ssh_host_ed25519_key",
        "ciphers aes128-ctr",
        "macs hmac-md5",
    ]

    output = parse_config(config)
    assert isinstance(output, OpenSshConfig)
    assert len(output.permit_root_login) == 1
    assert output.permit_root_login[0].value == "prohibit-password"
    assert output.use_privilege_separation == "no"
    assert output.protocol == "2"
    assert output.ciphers == "aes128-ctr"
    assert output.macs == "hmac-md5"


def test_parse_config_case():
    config = [
        "PermitRootLogin prohibit-password",
        "UsePrivilegeSeparation yes",
        "Protocol 1",
    ]

    output = parse_config(config)
    assert isinstance(output, OpenSshConfig)
    assert len(output.permit_root_login) == 1
    assert output.permit_root_login[0].value == "prohibit-password"
    assert output.use_privilege_separation == "yes"
    assert output.protocol == "1"


def test_parse_config_multiple():
    config = [
        "PermitRootLogin prohibit-password",
        "PermitRootLogin no",
        "PermitRootLogin yes",
        "Ciphers aes128-cbc",
        "Ciphers aes256-cbc",
    ]

    output = parse_config(config)
    assert isinstance(output, OpenSshConfig)
    assert len(output.permit_root_login) == 3
    assert output.permit_root_login[0].value == "prohibit-password"
    assert output.permit_root_login[1].value == "no"
    assert output.permit_root_login[2].value == "yes"
    assert output.use_privilege_separation is None
    assert output.protocol is None
    assert output.ciphers == 'aes128-cbc'


def test_parse_config_commented():
    config = [
        "#PermitRootLogin no",
        "#UsePrivilegeSeparation no",
        "#Protocol 12",
    ]

    output = parse_config(config)
    assert isinstance(output, OpenSshConfig)
    assert not output.permit_root_login
    assert output.use_privilege_separation is None
    assert output.protocol is None


def test_parse_config_missing_argument():
    config = [
        "PermitRootLogin",
        "UsePrivilegeSeparation",
        "Protocol"
    ]

    output = parse_config(config)
    assert isinstance(output, OpenSshConfig)
    assert not output.permit_root_login
    assert output.use_privilege_separation is None
    assert output.protocol is None


def test_parse_config_match():
    config = [
        "PermitRootLogin yes",
        "Match address 192.168.*",
        "   PermitRootLogin no"
    ]

    output = parse_config(config)
    assert isinstance(output, OpenSshConfig)
    assert len(output.permit_root_login) == 2
    assert output.permit_root_login[0].value == 'yes'
    assert output.permit_root_login[0].in_match is None
    assert output.permit_root_login[1].value == 'no'
    assert output.permit_root_login[1].in_match == ['address', '192.168.*']
    assert output.use_privilege_separation is None
    assert output.protocol is None


def test_parse_config_deprecated():
    config = [
        "permitrootlogin without-password"
    ]
    output = parse_config(config)
    assert isinstance(output, OpenSshConfig)
    assert len(output.permit_root_login) == 1
    assert output.permit_root_login[0].value == "prohibit-password"


def test_parse_config_empty():
    output = parse_config([])
    assert isinstance(output, OpenSshConfig)
    assert isinstance(output, OpenSshConfig)
    assert not output.permit_root_login
    assert output.use_privilege_separation is None
    assert output.protocol is None


def test_parse_config_modification():
    # This one was modified
    data = [
        "S.5....T.  c /etc/ssh/sshd_config",
    ]
    assert parse_config_modification(data)

    # This one was just touched (timestamp does not match)
    data = [
        ".......T.  c /etc/ssh/sshd_config",
    ]
    assert not parse_config_modification(data)

    # This one was not modified (not listed at all)
    data = [
        ".......T.  c /etc/sysconfig/sshd",
    ]
    assert not parse_config_modification(data)

    # Parse multiple lines
    data = [
        "S.5....T.  c /etc/sysconfig/sshd",
        "S.5....T.  c /etc/ssh/sshd_config",
    ]
    assert parse_config_modification(data)


def test_produce_config():
    output = []

    def fake_producer(*args):
        output.extend(args)

    config = OpenSshConfig(
        permit_root_login=[OpenSshPermitRootLogin(value="no")],
        use_privilege_separation="yes",
        protocol="1",
    )

    produce_config(fake_producer, config)
    assert len(output) == 1
    cfg = output[0]
    assert len(cfg.permit_root_login) == 1
    assert cfg.permit_root_login[0].value == "no"
    assert cfg.use_privilege_separation == "yes"
    assert cfg.protocol == '1'


def test_actor_execution(current_actor_context):
    current_actor_context.run()
    assert current_actor_context.consume(OpenSshConfig)
