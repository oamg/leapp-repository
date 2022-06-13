from leapp.libraries.common.rpms import _parse_config_modification


def test_parse_config_modification():
    # Empty means no modification
    data = []
    assert not _parse_config_modification(data, "/etc/ssh/sshd_config")

    # This one was modified
    data = [
        "S.5....T.  c /etc/ssh/sshd_config",
    ]
    assert _parse_config_modification(data, "/etc/ssh/sshd_config")

    # This one was just touched (timestamp does not match)
    data = [
        ".......T.  c /etc/ssh/sshd_config",
    ]
    assert not _parse_config_modification(data, "/etc/ssh/sshd_config")

    # This one was not modified (not listed at all)
    data = [
        ".......T.  c /etc/sysconfig/sshd",
    ]
    assert not _parse_config_modification(data, "/etc/ssh/sshd_config")

    # Parse multiple lines
    data = [
        "S.5....T.  c /etc/sysconfig/sshd",
        "S.5....T.  c /etc/ssh/sshd_config",
    ]
    assert _parse_config_modification(data, "/etc/ssh/sshd_config")
