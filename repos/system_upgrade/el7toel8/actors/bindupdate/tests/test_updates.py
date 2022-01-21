from leapp.libraries.actor import updates
from leapp.libraries.common import isccfg
from leapp.models import BindFacts


def test_simple():
    """Test configuration is not modified without offending statements."""
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
    parser = isccfg.IscConfigParser(mockcfg)
    modified = updates.update_config(parser, mockcfg)
    assert modified == mockcfg.buffer


def test_dnssec_lookaside():
    """Test unsupported statements are removed."""
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
    parser = isccfg.IscConfigParser(mockcfg)
    modified = updates.update_config(parser, mockcfg)
    assert modified != mockcfg.buffer
