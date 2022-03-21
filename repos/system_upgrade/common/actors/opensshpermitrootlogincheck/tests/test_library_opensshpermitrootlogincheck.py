from leapp.libraries.actor.opensshpermitrootlogincheck import global_value, semantics_changes
from leapp.models import OpenSshConfig, OpenSshPermitRootLogin


def test_empty_file():
    """ Empty file
    """
    config = OpenSshConfig(
        permit_root_login=[
        ],
        deprecated_directives=[]
    )

    assert semantics_changes(config)
    assert global_value(config, "default") == "default"


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
        deprecated_directives=[]
    )

    assert not semantics_changes(config)
    assert global_value(config, "default") == "yes"


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
        deprecated_directives=[]
    )

    assert not semantics_changes(config)
    assert global_value(config, "default") == "no"


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
        deprecated_directives=[]
    )

    assert not semantics_changes(config)
    assert global_value(config, "default") == "prohibit-password"


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
        deprecated_directives=[]
    )

    assert semantics_changes(config)
    assert global_value(config, "default") == "default"


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
        deprecated_directives=[]
    )

    assert semantics_changes(config)
    assert global_value(config, "default") == "default"


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
        deprecated_directives=[]
    )

    assert not semantics_changes(config)
    assert global_value(config, "default") == "default"


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
        deprecated_directives=[]
    )

    assert not semantics_changes(config)
    assert global_value(config, "default") == "no"


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
        deprecated_directives=[]
    )

    assert not semantics_changes(config)
    assert global_value(config, "default") == "prohibit-password"


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
        deprecated_directives=[]
    )

    assert not semantics_changes(config)
    assert global_value(config, "default") == "yes"


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
        deprecated_directives=[]
    )

    assert not semantics_changes(config)
    assert global_value(config, "default") == "no"


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
        deprecated_directives=[]
    )

    assert not semantics_changes(config)
    assert global_value(config, "default") == "yes"
