from leapp.libraries.actor.opensshpermitrootlogincheck import semantics_changes
from leapp.models import OpenSshConfig, OpenSshPermitRootLogin


def test_globally_enabled():
    """ Configuration file in this format:

        PermitRootLogin yes # explicit
    """
    config = OpenSshConfig(
        permit_root_login=[
            OpenSshPermitRootLogin(
                value='yes',
                in_match=None)
        ],
    )

    assert not semantics_changes(config)


def test_globally_disabled():
    """ Configuration file in this format:

        PermitRootLogin no # explicit
    """
    config = OpenSshConfig(
        permit_root_login=[
            OpenSshPermitRootLogin(
                value='no',
                in_match=None)
        ],
    )

    assert not semantics_changes(config)


def test_globally_disabled_password():
    """ Configuration file in this format:

        PermitRootLogin prohibit-password # explicit
    """
    config = OpenSshConfig(
        permit_root_login=[
            OpenSshPermitRootLogin(
                value='prohibit-password',
                in_match=None)
        ],
    )

    assert not semantics_changes(config)


def test_in_match_disabled():
    """ Configuration file in this format:

        # PermitRootLogin yes # implicit
        Match address 10.10.*
            PermitRootLogin no
    """
    config = OpenSshConfig(
        permit_root_login=[
            OpenSshPermitRootLogin(
                value='no',
                in_match=['address', '10.10.*'])
        ],
    )

    assert semantics_changes(config)


def test_in_match_disabled_password():
    """ Configuration file in this format:

        # PermitRootLogin yes # implicit
        Match address 192.168.*
            PermitRootLogin prohibit-password
    """
    config = OpenSshConfig(
        permit_root_login=[
            OpenSshPermitRootLogin(
                value='prohibit-password',
                in_match=['address', '10.10.*'])
        ],
    )

    assert semantics_changes(config)


def test_in_match_enabled():
    """ Configuration file in this format:

        # PermitRootLogin yes # implicit
        Match address 192.168.*
            PermitRootLogin yes
    """
    # TODO This is suspicious configuration we should probably handle separately
    config = OpenSshConfig(
        permit_root_login=[
            OpenSshPermitRootLogin(
                value='yes',
                in_match=['address', '192.168.*'])
        ],
    )

    assert not semantics_changes(config)


def test_in_match_all_disabled():
    """ Configuration file in this format:

        # PermitRootLogin yes # implicit
        Match all
            PermitRootLogin no
    """
    config = OpenSshConfig(
        permit_root_login=[
            OpenSshPermitRootLogin(
                value='no',
                in_match=['all'])
        ],
    )

    assert not semantics_changes(config)


def test_in_match_all_disabled_password():
    """ Configuration file in this format:

        # PermitRootLogin yes # implicit
        Match all
            PermitRootLogin prohibit-password
    """
    config = OpenSshConfig(
        permit_root_login=[
            OpenSshPermitRootLogin(
                value='prohibit-password',
                in_match=['all'])
        ],
    )

    assert not semantics_changes(config)


def test_in_match_all_enabled():
    """ Configuration file in this format:

        # PermitRootLogin yes # implicit
        Match all
            PermitRootLogin yes
    """
    config = OpenSshConfig(
        permit_root_login=[
            OpenSshPermitRootLogin(
                value='yes',
                in_match=['all'])
        ],
    )

    assert not semantics_changes(config)


def test_in_match_enabled_globally_disabled():
    """ Configuration file in this format:

        PermitRootLogin no # explicit
        Match address 192.*
            PermitRootLogin yes
    """
    config = OpenSshConfig(
        permit_root_login=[
            OpenSshPermitRootLogin(
                value='no',
                in_match=None),
            OpenSshPermitRootLogin(
                value='yes',
                in_match=['address', '192.*'])
        ],
    )

    assert not semantics_changes(config)


def test_in_match_disabled_globally_enabled():
    """ Configuration file in this format:

        PermitRootLogin yes # explicit
        Match address 192.*
            PermitRootLogin no
    """
    config = OpenSshConfig(
        permit_root_login=[
            OpenSshPermitRootLogin(
                value='yes',
                in_match=None),
            OpenSshPermitRootLogin(
                value='no',
                in_match=['address', '192.*'])
        ],
    )

    assert not semantics_changes(config)
