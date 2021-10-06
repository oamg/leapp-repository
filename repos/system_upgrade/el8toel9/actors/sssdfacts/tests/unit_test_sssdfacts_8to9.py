import textwrap

from six import StringIO

from leapp.libraries.actor.sssdfacts8to9 import SSSDFactsLibrary
from leapp.libraries.common import utils


def get_config(content):
    return utils.parse_config(StringIO(textwrap.dedent(content)))


def test_empty_config():
    config = utils.parse_config()
    facts = SSSDFactsLibrary(config).process()

    assert not facts.enable_files_domain_set
    assert not facts.explicit_files_domain
    assert not facts.pam_cert_auth


def test_enable_files_domain_set__notset():
    config = get_config("""
    [sssd]
    """)

    facts = SSSDFactsLibrary(config).process()

    assert not facts.enable_files_domain_set
    assert not facts.explicit_files_domain
    assert not facts.pam_cert_auth


def test_enable_files_domain_set__set_true():
    config = get_config("""
    [sssd]
    enable_files_domain = true
    """)

    facts = SSSDFactsLibrary(config).process()

    assert facts.enable_files_domain_set
    assert not facts.explicit_files_domain
    assert not facts.pam_cert_auth


def test_enable_files_domain_set__set_false():
    config = get_config("""
    [sssd]
    enable_files_domain = false
    """)

    facts = SSSDFactsLibrary(config).process()

    assert facts.enable_files_domain_set
    assert not facts.explicit_files_domain
    assert not facts.pam_cert_auth


def test_enable_files_domain_set__nodomain():
    config = get_config("""
    [sssd]
    """)

    facts = SSSDFactsLibrary(config).process()

    assert not facts.enable_files_domain_set
    assert not facts.explicit_files_domain
    assert not facts.pam_cert_auth


def test_explicit_files_domain__notset():
    config = get_config("""
    [sssd]
    domains = ldap

    [domain/ldap]
    id_provider = ldap
    """)

    facts = SSSDFactsLibrary(config).process()

    assert not facts.enable_files_domain_set
    assert not facts.explicit_files_domain
    assert not facts.pam_cert_auth


def test_explicit_files_domain__set():
    config = get_config("""
    [sssd]
    domains = files

    [domain/files]
    id_provider = files
    """)

    facts = SSSDFactsLibrary(config).process()

    assert not facts.enable_files_domain_set
    assert facts.explicit_files_domain
    assert not facts.pam_cert_auth


def test_pam_cert_auth__notset():
    config = get_config("""
    [pam]
    pam_gssapi_services = sudo
    """)

    facts = SSSDFactsLibrary(config).process()

    assert not facts.enable_files_domain_set
    assert not facts.explicit_files_domain
    assert not facts.pam_cert_auth


def test_pam_cert_auth__true():
    config = get_config("""
    [pam]
    pam_gssapi_services = sudo
    pam_cert_auth = true
    """)

    facts = SSSDFactsLibrary(config).process()

    assert not facts.enable_files_domain_set
    assert not facts.explicit_files_domain
    assert facts.pam_cert_auth


def test_pam_cert_auth__false():
    config = get_config("""
    [pam]
    pam_gssapi_services = sudo
    pam_cert_auth = false
    """)

    facts = SSSDFactsLibrary(config).process()

    assert not facts.enable_files_domain_set
    assert not facts.explicit_files_domain
    assert not facts.pam_cert_auth


def test_complex_config():
    config = get_config("""
    [sssd]
    user = root
    services = nss, pam, sudo
    domain = ldap, files

    [pam]
    pam_cert_auth = true

    [domain/ldap]
    id_provider = ldap
    ldap_groups_use_matching_rule_in_chain = True

    [domain/files]
    id_provider = files
    """)

    facts = SSSDFactsLibrary(config).process()

    assert not facts.enable_files_domain_set
    assert facts.explicit_files_domain
    assert facts.pam_cert_auth
