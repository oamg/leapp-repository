#!/usr/bin/env python
#
# Tests for bind configuration parsing

from leapp.libraries.common import isccfg

#
# Sample configuration stubs
#
named_conf_default = isccfg.MockConfig("""
//
// named.conf
//
// Provided by Red Hat bind package to configure the ISC BIND named(8) DNS
// server as a caching only nameserver (as a localhost DNS resolver only).
//
// See /usr/share/doc/bind*/sample/ for example named configuration files.
//

options {
    listen-on port 53 { 127.0.0.1; };
    listen-on-v6 port 53 { ::1; };
    directory      "/var/named";
    dump-file      "/var/named/data/cache_dump.db";
    statistics-file "/var/named/data/named_stats.txt";
    memstatistics-file "/var/named/data/named_mem_stats.txt";
    secroots-file   "/var/named/data/named.secroots";
    recursing-file  "/var/named/data/named.recursing";
    allow-query     { localhost; };

    /*
     - If you are building an AUTHORITATIVE DNS server, do NOT enable recursion.
     - If you are building a RECURSIVE (caching) DNS server, you need to enable
       recursion.
     - If your recursive DNS server has a public IP address, you MUST enable access
       control to limit queries to your legitimate users. Failing to do so will
       cause your server to become part of large scale DNS amplification
       attacks. Implementing BCP38 within your network would greatly
       reduce such attack surface
    */
    recursion yes;

    dnssec-enable yes;
    dnssec-validation yes;

    managed-keys-directory "/var/named/dynamic";

    pid-file "/run/named/named.pid";
    session-keyfile "/run/named/session.key";
};

logging {
        channel default_debug {
                file "data/named.run";
                severity dynamic;
        };
};

zone "." IN {
    type hint;
    file "named.ca";
};

# Avoid including files from bind package, may be not installed
# include "/etc/named.rfc1912.zones";
# include "/etc/named.root.key";
include "/dev/null";
""")


options_lookaside_no = isccfg.MockConfig("""
options {
    dnssec-lookaside no;
};
""")


options_lookaside_auto = isccfg.MockConfig("""
options {
    dnssec-lookaside /* no */ auto;
};
""")


options_lookaside_manual = isccfg.MockConfig("""
options {
    # make sure parser handles comments
    dnssec-lookaside "." /* comment to confuse parser */trust-anchor "dlv.isc.org";
};
""")


options_lookaside_commented = isccfg.MockConfig("""
options {
    /* dnssec-lookaside auto; */
};
""")


views_lookaside = isccfg.MockConfig("""
view "v1" IN {
    // This is auto
    dnssec-lookaside auto;
};

options {
    /* This is multi
     * line
     * comment */
    dnssec-lookaside no;
};

view "v2" {
    # Note no IN
    dnssec-lookaside "." trust-anchor "dlv.isc.org";
};
""")

config_empty = isccfg.MockConfig('')

config_empty_include = isccfg.MockConfig('options { include "/dev/null"; };')


def check_in_section(parser, section, key, value):
    """ Helper to check some section was found
        in configuration section and has expected value

        :type parser: IscConfigParser
        :type section: bind.ConfigSection
        :type key: str
        :param value: expected value """
    assert isinstance(section, isccfg.ConfigSection)
    cfgval = parser.find_val_section(section, key)
    assert isinstance(cfgval, isccfg.ConfigSection)
    assert cfgval.value() == value
    return cfgval


def cb_state(statement, state):
    """Callback used in IscConfigParser.walk()"""
    key = statement.var(0).value()
    state[key] = statement


def find_options(parser):
    """Replace IscConfigParser.find_option with walk use"""
    state = {}
    callbacks = {
        'options': cb_state,
    }
    assert len(parser.FILES_TO_CHECK) >= 1
    cfg = parser.FILES_TO_CHECK[0]
    parser.walk(cfg.root_section(), callbacks, state)
    options = state['options']
    if options:
        assert isinstance(options, isccfg.ConfigVariableSection)
        return options.firstblock()
    return None


# End of helpers
#
# Begin of tests


def test_lookaside_no():
    parser = isccfg.IscConfigParser(options_lookaside_no)
    assert len(parser.FILES_TO_CHECK) == 1
    opt = find_options(parser)
    check_in_section(parser, opt, "dnssec-lookaside", "no")


def test_lookaside_commented():
    parser = isccfg.IscConfigParser(options_lookaside_commented)
    assert len(parser.FILES_TO_CHECK) == 1
    opt = find_options(parser)
    assert isinstance(opt, isccfg.ConfigSection)
    lookaside = parser.find_val_section(opt, "dnssec-lookaside")
    assert lookaside is None


def test_default():
    parser = isccfg.IscConfigParser(named_conf_default)
    assert len(parser.FILES_TO_CHECK) >= 2
    opt = find_options(parser)
    check_in_section(parser, opt, "directory", '"/var/named"')
    check_in_section(parser, opt, "session-keyfile", '"/run/named/session.key"')
    check_in_section(parser, opt, "allow-query", '{ localhost; }')
    check_in_section(parser, opt, "recursion", 'yes')
    check_in_section(parser, opt, "dnssec-validation", 'yes')
    check_in_section(parser, opt, "dnssec-enable", 'yes')


def test_key_lookaside():
    parser = isccfg.IscConfigParser(options_lookaside_manual)
    opt = find_options(parser)
    key = parser.find_next_key(opt.config, opt.start+1, opt.end)
    assert isinstance(key, isccfg.ConfigSection)
    assert key.value() == 'dnssec-lookaside'
    value = parser.find_next_val(opt.config, None, key.end+1, opt.end)
    assert value.value() == '"."'
    key2 = parser.find_next_key(opt.config, value.end+1, opt.end)
    assert key2.value() == 'trust-anchor'
    value2a = parser.find_next_val(opt.config, None, key2.end+1, opt.end)
    value2b = parser.find_val(opt.config, 'trust-anchor', value.end+1, opt.end)
    assert value2b.value() == '"dlv.isc.org"'
    assert value2a.value() == value2b.value()
    value3 = parser.find_next_key(opt.config, value2b.end+1, opt.end, end_report=True)
    assert value3.value() == ';'


def test_key_lookaside_all():
    """ Test getting variable arguments after keyword """
    parser = isccfg.IscConfigParser(options_lookaside_manual)
    assert len(parser.FILES_TO_CHECK) == 1
    opt = find_options(parser)
    assert isinstance(opt, isccfg.ConfigSection)
    values = parser.find_values(opt, "dnssec-lookaside")
    assert values is not None
    assert len(values) >= 4
    key = values[0].value()
    assert key == 'dnssec-lookaside'
    assert values[1].value() == '"."'
    assert values[2].value() == 'trust-anchor'
    assert values[3].value() == '"dlv.isc.org"'
    assert values[4].value() == ';'


def test_key_lookaside_simple():
    """ Test getting variable arguments after keyword """
    parser = isccfg.IscConfigParser(options_lookaside_manual)
    assert len(parser.FILES_TO_CHECK) == 1
    stmts = parser.find('options.dnssec-lookaside')
    assert stmts is not None
    assert len(stmts) == 1
    assert isinstance(stmts[0], isccfg.ConfigVariableSection)
    values = stmts[0].values
    assert len(values) >= 4
    key = values[0].value()
    assert key == 'dnssec-lookaside'
    assert values[1].value() == '"."'
    assert values[2].value() == 'trust-anchor'
    assert values[3].value() == '"dlv.isc.org"'
    assert values[4].value() == ';'


def test_find_index():
    """ Test simplified searching for values in sections """
    parser = isccfg.IscConfigParser(named_conf_default)
    assert len(parser.FILES_TO_CHECK) >= 1
    stmts = parser.find('logging.channel.severity')
    assert stmts is not None and len(stmts) == 1
    assert isinstance(stmts[0], isccfg.ConfigVariableSection)
    values = stmts[0].values
    assert len(values) >= 1
    key = values[0].value()
    assert key == 'severity'
    assert values[1].value() == 'dynamic'
    recursion = parser.find('options.recursion')
    assert len(recursion) == 1 and len(recursion[0].values) >= 2
    assert recursion[0].values[0].value() == 'recursion'
    assert recursion[0].values[1].value() == 'yes'


def cb_view(statement, state):
    if 'view' not in state:
        state['view'] = {}
    name = statement.var(1).invalue()
    second = statement.var(2)
    if second.type() != isccfg.ConfigSection.TYPE_BLOCK:
        name = second.value() + '_' + name
    state['view'][name] = statement


def test_key_views_lookaside():
    """ Test getting variable arguments for views """

    parser = isccfg.IscConfigParser(views_lookaside)
    assert len(parser.FILES_TO_CHECK) == 1
    opt = find_options(parser)
    assert isinstance(opt, isccfg.ConfigSection)
    opt_val = parser.find_values(opt, "dnssec-lookaside")
    assert isinstance(opt_val[1], isccfg.ConfigSection)
    assert opt_val[1].value() == 'no'

    state = {}
    callbacks = {
        'view': cb_view,
    }
    assert len(parser.FILES_TO_CHECK) >= 1
    cfg = parser.FILES_TO_CHECK[0]
    parser.walk(cfg.root_section(), callbacks, state)

    views = state['view']
    assert len(views) == 2

    v1 = views['IN_v1']
    assert isinstance(v1, isccfg.ConfigVariableSection)
    v1b = v1.firstblock()
    assert isinstance(v1b, isccfg.ConfigSection)
    v1_la = parser.find_val_section(v1b, "dnssec-lookaside")
    assert isinstance(v1_la, isccfg.ConfigSection)
    assert v1_la.value() == 'auto'

    v2 = views['v2']
    assert isinstance(v2, isccfg.ConfigVariableSection)
    v2b = v2.firstblock()
    assert isinstance(v2b, isccfg.ConfigSection)
    v2_la = parser.find_values(v2b, "dnssec-lookaside")
    assert isinstance(v2_la[1], isccfg.ConfigSection)
    assert v2_la[1].value() == '"."'
    assert isinstance(v2_la[3], isccfg.ConfigSection)
    assert v2_la[3].value() == '"dlv.isc.org"'


def test_remove_comments():
    """ Test removing comments works as expected """

    parser = isccfg.IscConfigParser(views_lookaside)
    assert len(parser.FILES_TO_CHECK) == 1
    cfg = parser.FILES_TO_CHECK[0]
    assert isinstance(cfg, isccfg.ConfigFile)
    removed_comments = parser._remove_comments(cfg.buffer)
    assert len(removed_comments) < len(cfg.buffer)
    replaced_comments = parser._replace_comments(cfg.buffer)
    assert len(replaced_comments) == len(cfg.buffer)
    assert 'This is auto' not in replaced_comments
    assert 'comment' not in replaced_comments
    assert 'Note no IN' not in replaced_comments


def test_walk():
    """ Test walk function of parser """

    callbacks = {
        'options': cb_state,
        'dnssec-lookaside': cb_state,
        'dnssec-validation': cb_state,
    }
    state = {}
    parser = isccfg.IscConfigParser(views_lookaside)
    assert len(parser.FILES_TO_CHECK) == 1
    cfg = parser.FILES_TO_CHECK[0]
    parser.walk(cfg.root_section(), callbacks, state)
    assert 'options' in state
    assert 'dnssec-lookaside' in state
    assert 'dnssec-validation' not in state


def test_empty_config():
    """ Test empty configuration """

    callbacks = {}

    parser = isccfg.IscConfigParser(config_empty)
    assert len(parser.FILES_TO_CHECK) == 1
    cfg = parser.FILES_TO_CHECK[0]
    parser.walk(cfg.root_section(), callbacks)
    assert cfg.buffer == ''


def test_empty_include_config():
    """ Test empty configuration """

    callbacks = {}

    parser = isccfg.IscConfigParser(config_empty_include)
    assert len(parser.FILES_TO_CHECK) == 2
    cfg = parser.FILES_TO_CHECK[0]
    parser.walk(cfg.root_section(), callbacks)
    assert cfg.buffer == 'options { include "/dev/null"; };'

    null_cfg = parser.FILES_TO_CHECK[1]
    parser.walk(null_cfg.root_section(), callbacks)
    assert null_cfg.buffer == ''


if __name__ == '__main__':
    test_key_views_lookaside()
