import pytest

from leapp.libraries.actor.config_parser import ParsingError, VsftpdConfigOptionParser, VsftpdConfigParser


def test_VsftpdConfigOptionParser_invalid_syntax():
    parser = VsftpdConfigOptionParser()

    with pytest.raises(ParsingError):
        parser.parse_value('unknown option', 'foo')
    with pytest.raises(ParsingError):
        parser.parse_value('anonymous_enable', 'non-boolean value')
    with pytest.raises(ParsingError):
        parser.parse_value('require_cert', 'non-boolean value')
    with pytest.raises(ParsingError):
        parser.parse_value('anon_mkdir_write_enable', '')
    with pytest.raises(ParsingError):
        parser.parse_value('accept_timeout', 'non-integer value')
    with pytest.raises(ParsingError):
        parser.parse_value('max_per_ip', 'non-integer value')
    with pytest.raises(ParsingError):
        parser.parse_value('listen_port', '')


def test_VsftpdConfigOptionParser_string_option():
    parser = VsftpdConfigOptionParser()

    assert parser.parse_value('secure_chroot_dir', 'foo') == 'foo'
    assert parser.parse_value('user_config_dir', '') == ''
    assert parser.parse_value('dsa_cert_file', 'value with spaces') == 'value with spaces'


def test_VsftpdConfigOptionParser_boolean_option():
    parser = VsftpdConfigOptionParser()

    assert parser.parse_value('background', 'TRUE') is True
    assert parser.parse_value('run_as_launching_user', 'true') is True
    assert parser.parse_value('no_log_lock', 'YES') is True
    assert parser.parse_value('force_local_data_ssl', 'yES') is True
    assert parser.parse_value('ssl_tlsv1_2', '1') is True

    assert parser.parse_value('background', 'FALSE') is False
    assert parser.parse_value('run_as_launching_user', 'false') is False
    assert parser.parse_value('no_log_lock', 'NO') is False
    assert parser.parse_value('force_local_data_ssl', 'No') is False
    assert parser.parse_value('ssl_tlsv1_2', '0') is False


def test_VsftpdConfigOptionParser_integer_option():
    parser = VsftpdConfigOptionParser()

    assert parser.parse_value('connect_timeout', '0') == 0
    assert parser.parse_value('idle_session_timeout', '1') == 1
    assert parser.parse_value('data_connection_timeout', '2') == 2
    assert parser.parse_value('pasv_max_port', '6234') == 6234


def test_VsftpdConfigParser_invalid_syntax():
    with pytest.raises(ParsingError):
        VsftpdConfigParser('unknown_option=foo')
    with pytest.raises(ParsingError):
        VsftpdConfigParser('anonymous_enable=non-boolean')
    with pytest.raises(ParsingError):
        VsftpdConfigParser(' # comment with whitespace before the # character')
    with pytest.raises(ParsingError):
        VsftpdConfigParser('anonymous_enable')

    # Make sure that line num is properly shown
    with pytest.raises(ParsingError) as err:
        VsftpdConfigParser('background=0\n#andthislineisalso=fine\nError on line 3')
    assert "Syntax error on line 3" in str(err.value)


def test_VsftpdConfigParser_empty_config():
    parser = VsftpdConfigParser('')
    assert isinstance(parser.parsed_config, dict)
    assert not parser.parsed_config


def test_VsftpdConfigParser_only_comments():
    parser = VsftpdConfigParser('# foo\n\n#bar\n')
    assert isinstance(parser.parsed_config, dict)
    assert not parser.parsed_config

    parser = VsftpdConfigParser('#anonymous_enable=yes\n')
    assert isinstance(parser.parsed_config, dict)
    assert not parser.parsed_config


def test_VsftpdConfigParser_one_option():
    parser = VsftpdConfigParser('anonymous_enable=yes\n')
    assert len(parser.parsed_config) == 1
    assert parser.parsed_config['anonymous_enable'] is True


def test_VsftpdConfigParser_multiple_options():
    content = '# foo\n\nanonymous_enable=no\nbanned_email_file=/foo/bar\n# bar\nmax_login_fails=3\n'
    parser = VsftpdConfigParser(content)

    assert len(parser.parsed_config) == 3
    assert parser.parsed_config['anonymous_enable'] is False
    assert parser.parsed_config['banned_email_file'] == '/foo/bar'
    assert parser.parsed_config['max_login_fails'] == 3
