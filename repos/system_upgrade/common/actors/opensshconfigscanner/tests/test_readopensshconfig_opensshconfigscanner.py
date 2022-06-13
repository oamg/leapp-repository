from leapp.libraries.actor.readopensshconfig import line_empty, parse_config, produce_config
from leapp.models import OpenSshConfig, OpenSshPermitRootLogin


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
        "subsystem sftp internal-sftp",
        "subsystem other internal-other",  # this is ignored
    ]

    output = parse_config(config)
    assert isinstance(output, OpenSshConfig)
    assert len(output.permit_root_login) == 1
    assert output.permit_root_login[0].value == "prohibit-password"
    assert output.use_privilege_separation == "no"
    assert output.protocol == "2"
    assert output.ciphers == "aes128-ctr"
    assert output.macs == "hmac-md5"
    assert output.subsystem_sftp == "internal-sftp"


def test_parse_config_case():
    config = [
        "PermitRootLogin prohibit-password",
        "UsePrivilegeSeparation yes",
        "Protocol 1",
        "SubSystem sftp sftp-server",
    ]

    output = parse_config(config)
    assert isinstance(output, OpenSshConfig)
    assert len(output.permit_root_login) == 1
    assert output.permit_root_login[0].value == "prohibit-password"
    assert output.use_privilege_separation == "yes"
    assert output.protocol == "1"
    assert output.subsystem_sftp == "sftp-server"


def test_parse_config_multiple():
    config = [
        "PermitRootLogin prohibit-password",
        "PermitRootLogin no",
        "PermitRootLogin yes",
        "Ciphers aes128-cbc",
        "Ciphers aes256-cbc",
        "subsystem sftp internal-sftp",
        "subsystem sftp internal-sftp2",
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
    assert output.subsystem_sftp == 'internal-sftp'


def test_parse_config_commented():
    config = [
        "#PermitRootLogin no",
        "#UsePrivilegeSeparation no",
        "#Protocol 12",
        "#SubSystem sftp internal-sftp",
    ]

    output = parse_config(config)
    assert isinstance(output, OpenSshConfig)
    assert not output.permit_root_login
    assert output.use_privilege_separation is None
    assert output.protocol is None
    assert output.subsystem_sftp is None


def test_parse_config_missing_argument():
    config = [
        "PermitRootLogin",
        "UsePrivilegeSeparation",
        "Protocol"
        "SubSystem"
        "SubSystem sftp"
    ]

    output = parse_config(config)
    assert isinstance(output, OpenSshConfig)
    assert not output.permit_root_login
    assert output.use_privilege_separation is None
    assert output.protocol is None
    assert output.subsystem_sftp is None


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


def test_produce_config():
    output = []

    def fake_producer(*args):
        output.extend(args)

    config = OpenSshConfig(
        permit_root_login=[OpenSshPermitRootLogin(value="no")],
        use_privilege_separation="yes",
        protocol="1",
        deprecated_directives=[],
        subsystem_sftp="internal-sftp",
    )

    produce_config(fake_producer, config)
    assert len(output) == 1
    cfg = output[0]
    assert len(cfg.permit_root_login) == 1
    assert cfg.permit_root_login[0].value == "no"
    assert cfg.use_privilege_separation == "yes"
    assert cfg.protocol == '1'
    assert cfg.subsystem_sftp == 'internal-sftp'


def test_actor_execution(current_actor_context):
    current_actor_context.run()
    assert current_actor_context.consume(OpenSshConfig)
