import glob
import os
import shutil
import tempfile

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import readopensshconfig
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
    assert not output.permit_root_login
    assert output.use_privilege_separation is None
    assert output.protocol is None


def test_parse_config_include(monkeypatch):
    """ This already require some files to touch """

    config_contents = {
        '/etc/ssh/sshd_config': [
            "Include /path/*.conf"
        ],
        '/path/my.conf': [
            'Subsystem sftp internal-sftp'
        ],
        '/path/another.conf': [
            'permitrootlogin no'
        ]
    }

    primary_config_path = '/etc/ssh/sshd_config'
    primary_config_contents = config_contents[primary_config_path]

    def glob_mocked(pattern):
        assert pattern == '/path/*.conf'
        return ['/path/my.conf', '/path/another.conf']

    def read_config_mocked(path):
        return config_contents[path]

    monkeypatch.setattr(glob, 'glob', glob_mocked)
    monkeypatch.setattr(readopensshconfig, 'read_sshd_config', read_config_mocked)

    output = parse_config(primary_config_contents)

    assert isinstance(output, OpenSshConfig)
    assert len(output.permit_root_login) == 1
    assert output.permit_root_login[0].value == 'no'
    assert output.permit_root_login[0].in_match is None
    assert output.use_privilege_separation is None
    assert output.protocol is None
    assert output.subsystem_sftp == 'internal-sftp'


def test_parse_config_include_recursive(monkeypatch):
    """ The recursive include should gracefully fail """

    config_contents = {
        '/etc/ssh/sshd_config': [
            "Include /path/*.conf"
        ],
        '/path/recursive.conf': [
            "Include /path/*.conf"
        ],
    }

    primary_config_path = '/etc/ssh/sshd_config'
    primary_config_contents = config_contents[primary_config_path]

    def glob_mocked(pattern):
        assert pattern == '/path/*.conf'
        return ['/path/recursive.conf']

    def read_config_mocked(path):
        return config_contents[path]

    monkeypatch.setattr(glob, 'glob', glob_mocked)
    monkeypatch.setattr(readopensshconfig, 'read_sshd_config', read_config_mocked)

    with pytest.raises(StopActorExecutionError) as recursive_error:
        parse_config(primary_config_contents)
    assert 'Failed to parse sshd configuration file' in str(recursive_error)


def test_parse_config_include_relative(monkeypatch):
    """ When the include argument is relative path, it should point into the /etc/ssh/ """

    config_contents = {
        '/etc/ssh/sshd_config': [
            "Include relative/*.conf"
        ],
        '/etc/ssh/relative/default.conf': [
            'Match address 192.168.1.42',
            'PermitRootLogin yes'
        ],
        '/etc/ssh/relative/other.conf': [
            'Match all',
            'PermitRootLogin prohibit-password'
        ],
        '/etc/ssh/relative/wrong.extension': [
            "macs hmac-md5",
        ],
    }

    primary_config_path = '/etc/ssh/sshd_config'
    primary_config_contents = config_contents[primary_config_path]

    def glob_mocked(pattern):
        assert pattern == '/etc/ssh/relative/*.conf'
        return ['/etc/ssh/relative/other.conf', '/etc/ssh/relative/default.conf']

    def read_config_mocked(path):
        return config_contents[path]

    monkeypatch.setattr(glob, 'glob', glob_mocked)
    monkeypatch.setattr(readopensshconfig, 'read_sshd_config', read_config_mocked)

    output = parse_config(primary_config_contents)

    assert isinstance(output, OpenSshConfig)
    assert len(output.permit_root_login) == 2
    assert output.permit_root_login[0].value == 'yes'
    assert output.permit_root_login[0].in_match == ['address', '192.168.1.42']
    assert output.permit_root_login[1].value == 'prohibit-password'
    assert output.permit_root_login[1].in_match == ['all']
    assert output.use_privilege_separation is None
    assert output.ciphers is None
    assert output.macs is None
    assert output.protocol is None
    assert output.subsystem_sftp is None


def test_parse_config_include_complex(monkeypatch):
    """ This already require some files to touch """

    config_contents = {
        '/etc/ssh/sshd_config': [
            "Include /path/*.conf /other/path/*.conf \"/last/path with spaces/*.conf\" "
        ],
        '/path/my.conf': [
            'permitrootlogin prohibit-password'
        ],
        '/other/path/another.conf': [
            'ciphers aes128-ctr'
        ],
        '/last/path with spaces/filename with spaces.conf': [
            'subsystem sftp other-internal'
        ]
    }
    glob_contents = {
        '/path/*.conf': [
            '/path/my.conf'
        ],
        '/other/path/*.conf': [
            '/other/path/another.conf'
        ],
        '/last/path with spaces/*.conf': [
            '/last/path with spaces/filename with spaces.conf'
        ],
    }

    primary_config_path = '/etc/ssh/sshd_config'
    primary_config_contents = config_contents[primary_config_path]

    def glob_mocked(pattern):
        return glob_contents[pattern]

    def read_config_mocked(path):
        return config_contents[path]

    monkeypatch.setattr(glob, 'glob', glob_mocked)
    monkeypatch.setattr(readopensshconfig, 'read_sshd_config', read_config_mocked)

    output = parse_config(primary_config_contents)

    assert isinstance(output, OpenSshConfig)
    assert len(output.permit_root_login) == 1
    assert output.permit_root_login[0].value == 'prohibit-password'
    assert output.permit_root_login[0].in_match is None
    assert output.use_privilege_separation is None
    assert output.ciphers == "aes128-ctr"
    assert output.protocol is None
    assert output.subsystem_sftp == 'other-internal'


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
