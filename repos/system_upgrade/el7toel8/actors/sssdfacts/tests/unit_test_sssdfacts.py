import textwrap

from six import StringIO

from leapp.libraries.actor.sssdfacts import SSSDFactsLibrary
from leapp.libraries.common import utils
from leapp.models import SSSDConfig, SSSDDomainConfig


def get_config(content):
    parser = utils.parse_config(StringIO(textwrap.dedent(content)))
    return parser


def test_empty_config():
    config = utils.parse_config()
    facts = SSSDFactsLibrary(config).process()

    assert not facts.domains


def test_local_domain():
    config = get_config("""
    [domain/local]
    id_provider = local
    """)

    facts = SSSDFactsLibrary(config).process()

    assert len(facts.domains) == 1
    assert facts.domains[0].name == "local"
    assert len(facts.domains[0].options) == 1
    assert "local_provider" in facts.domains[0].options


def test_groups_chain():
    config = get_config("""
    [domain/ldap]
    id_provider = ldap
    ldap_groups_use_matching_rule_in_chain = True

    # Set this option to avoid reporting its change
    ldap_sudo_include_regexp = True
    """)

    facts = SSSDFactsLibrary(config).process()

    assert len(facts.domains) == 1
    assert facts.domains[0].name == "ldap"
    assert len(facts.domains[0].options) == 1
    assert "groups_chain" in facts.domains[0].options


def test_initgroups_chain():
    config = get_config("""
    [domain/ldap]
    id_provider = ldap
    ldap_initgroups_use_matching_rule_in_chain = True

    # Set this option to avoid reporting its change
    ldap_sudo_include_regexp = True
    """)

    facts = SSSDFactsLibrary(config).process()

    assert len(facts.domains) == 1
    assert facts.domains[0].name == "ldap"
    assert len(facts.domains[0].options) == 1
    assert "initgroups_chain" in facts.domains[0].options


def test_sudo_regexp__ldap():
    config = get_config("""
    [domain/ldap]
    id_provider = ldap
    """)

    facts = SSSDFactsLibrary(config).process()

    assert len(facts.domains) == 1
    assert facts.domains[0].name == "ldap"
    assert len(facts.domains[0].options) == 1
    assert "sudo_regexp" in facts.domains[0].options


def test_sudo_regexp__ad():
    config = get_config("""
    [domain/ad]
    id_provider = ad
    """)

    facts = SSSDFactsLibrary(config).process()

    assert len(facts.domains) == 1
    assert facts.domains[0].name == "ad"
    assert len(facts.domains[0].options) == 1
    assert "sudo_regexp" in facts.domains[0].options


def test_sudo_regexp__ipa():
    config = get_config("""
    [domain/ipa]
    id_provider = ipa
    """)

    facts = SSSDFactsLibrary(config).process()

    assert len(facts.domains) == 1
    assert facts.domains[0].name == "ipa"
    assert not facts.domains[0].options


def test_complex():
    config = get_config("""
    [sssd]
    user = root
    services = nss, pam, sudo

    [domain/local]
    id_provider = local

    [domain/ldap]
    id_provider = ldap
    ldap_groups_use_matching_rule_in_chain = True

    [domain/ipa]
    id_provider = ipa
    """)

    facts = SSSDFactsLibrary(config).process()

    assert len(facts.domains) == 3

    assert facts.domains[0].name == "local"
    assert len(facts.domains[0].options) == 1
    assert "local_provider" in facts.domains[0].options

    assert facts.domains[1].name == "ldap"
    assert len(facts.domains[1].options) == 2
    assert "groups_chain" in facts.domains[1].options
    assert "sudo_regexp" in facts.domains[1].options

    assert facts.domains[2].name == "ipa"
    assert not facts.domains[2].options


def test_get_domain_section():
    config = utils.parse_config()
    library = SSSDFactsLibrary(config)

    assert library.get_domain_section("ldap") == "domain/ldap"


def test_get_provider__none():
    config = get_config("""
    [domain/local]
    """)
    library = SSSDFactsLibrary(config)

    assert library.get_provider("local", "id_provider") is None


def test_get_provider__without_fallback():
    config = get_config("""
    [domain/local]
    id_provider = local
    """)
    library = SSSDFactsLibrary(config)

    assert library.get_provider("local", "id_provider") == "local"


def test_get_provider__with_fallback():
    config = get_config("""
    [domain/ldap]
    id_provider = ldap
    """)
    library = SSSDFactsLibrary(config)

    assert library.get_provider("ldap", "sudo_provider", ["id_provider"]) == "ldap"
