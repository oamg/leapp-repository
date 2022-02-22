from leapp.libraries.actor import iscmodel
from leapp.libraries.common import isccfg
from leapp.models import BindFacts


def model_paths(issues_model):
    paths = list()
    for m in issues_model:
        paths.append(m.path)
    return paths


def get_facts(cfg):
    facts = iscmodel.get_facts(cfg)
    assert isinstance(facts, BindFacts)
    return facts


def test_simple():
    mockcfg = isccfg.MockConfig("""
options {
    listen-on port 53 { 127.0.0.1; };
    listen-on-v6 port 53 { ::1; };
    directory       "/var/named";
    allow-query     { localhost; };
    recursion yes;

    dnssec-validation yes;
};

zone "." IN {
    type hint;
    file "named.ca";
};
""", '/etc/named.conf')
    facts = get_facts(mockcfg)
    assert facts.dnssec_lookaside is None


def test_dnssec_lookaside():
    mockcfg = isccfg.MockConfig("""
options {
    listen-on port 53 { 127.0.0.1; };
    listen-on-v6 port 53 { ::1; };
    directory       "/var/named";
    allow-query     { localhost; };
    recursion yes;

    dnssec-validation yes;
        dnssec-lookaside auto;
};

zone "." IN {
    type hint;
    file "named.ca";
};
""", '/etc/named.conf')
    facts = get_facts(mockcfg)
    assert '/etc/named.conf' in model_paths(facts.dnssec_lookaside)


def test_listen_on_v6():
    present = isccfg.MockConfig("""
options {
    listen-on { any; };
    listen-on-v6 { any; };
};
""", '/etc/named.conf')
    missing = isccfg.MockConfig("""
options {
    listen-on { any; };
    #listen-on-v6 { any; };
};
""", '/etc/named.conf')

    facts = get_facts(present)
    assert not facts.listen_on_v6_missing

    facts = get_facts(missing)
    assert facts.listen_on_v6_missing
