from leapp.libraries.actor import mpath_conf_check
from leapp.models import MultipathConfFacts9to10, MultipathConfig9to10
from leapp.reporting import Report


def _assert_config_dir_report(report):
    assert report['title'] == \
        'device-mapper-multipath custom config_dir is deprecated'
    assert report['severity'] == 'info'


def _assert_config_dir_conflict_report(report):
    assert report['title'] == \
        'device-mapper-multipath config_dir conflict'
    assert report['severity'] == 'high'


def _assert_files_report(report):
    assert report['title'] == \
        'device-mapper-multipath configuration files will be moved'
    assert report['severity'] == 'info'


def _assert_socket_activation_report(report):
    assert report['title'] == \
        'device-mapper-multipath socket activation is disabled by default'
    assert report['severity'] == 'info'


def _assert_dm_nvme_report(report):
    assert report['title'] == \
        'device-mapper-multipath NVMe multipathing is no longer supported'
    assert report['severity'] == 'info'


def _assert_getuid_report(report, paths_str):
    assert report['title'] == \
        'device-mapper-multipath configuration contains getuid_callout'
    assert report['severity'] == 'high'
    assert paths_str in report['summary']


def _build_config(pathname, config_dir=None, bindings_file=None,
                  wwids_file=None, prkeys_file=None,
                  has_socket_activation=False, has_dm_nvme_multipathing=False,
                  has_getuid=False):
    return MultipathConfig9to10(
        pathname=pathname,
        config_dir=config_dir,
        bindings_file=bindings_file,
        wwids_file=wwids_file,
        prkeys_file=prkeys_file,
        has_socket_activation=has_socket_activation,
        has_dm_nvme_multipathing=has_dm_nvme_multipathing,
        has_getuid=has_getuid,
    )


def _build_facts(confs):
    return MultipathConfFacts9to10(configs=confs)


def test_no_issues(current_actor_context):
    config = _build_config('no_issues.conf')
    facts = _build_facts([config])
    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = current_actor_context.consume(Report)
    assert not reports


def test_all_issues(current_actor_context, monkeypatch):
    monkeypatch.setattr(mpath_conf_check, '_default_config_dir_has_conf_files', lambda: False)
    config = _build_config(
        'all_issues.conf',
        config_dir='/etc/multipath/foo.d',
        bindings_file='/tmp/bindings',
        has_socket_activation=True,
        has_dm_nvme_multipathing=True,
        has_getuid=True)
    facts = _build_facts([config])
    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert reports and len(reports) == 5
    _assert_config_dir_report(reports[0].report)
    _assert_files_report(reports[1].report)
    _assert_socket_activation_report(reports[2].report)
    _assert_dm_nvme_report(reports[3].report)
    _assert_getuid_report(reports[4].report, 'all_issues.conf')


def test_config_dir_default(current_actor_context):
    config = _build_config('default_dir.conf',
                           config_dir='/etc/multipath/conf.d')
    facts = _build_facts([config])
    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = current_actor_context.consume(Report)
    assert not reports


def test_config_dir_nondefault(current_actor_context, monkeypatch):
    monkeypatch.setattr(mpath_conf_check, '_default_config_dir_has_conf_files', lambda: False)
    config = _build_config('custom_dir.conf',
                           config_dir='/etc/multipath/foo.d')
    facts = _build_facts([config])
    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert reports and len(reports) == 1
    _assert_config_dir_report(reports[0].report)


def test_files_nondefault(current_actor_context):
    config = _build_config('custom_files.conf',
                           bindings_file='/tmp/bindings',
                           wwids_file='/tmp/wwids')
    facts = _build_facts([config])
    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert reports and len(reports) == 1
    _assert_files_report(reports[0].report)
    assert '/tmp/bindings' in reports[0].report['summary']
    assert '/tmp/wwids' in reports[0].report['summary']


def test_files_overridden_by_secondary(current_actor_context):
    primary = _build_config('primary.conf',
                            bindings_file='/tmp/bindings')
    secondary = _build_config('secondary.conf',
                              bindings_file='/etc/multipath/bindings')
    facts = _build_facts([primary, secondary])
    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = current_actor_context.consume(Report)
    assert not reports


def test_files_secondary_overrides_to_nondefault(current_actor_context):
    primary = _build_config('primary.conf')
    secondary = _build_config('secondary.conf',
                              bindings_file='/tmp/bindings')
    facts = _build_facts([primary, secondary])
    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert reports and len(reports) == 1
    _assert_files_report(reports[0].report)


def test_socket_activation(current_actor_context):
    config = _build_config('socket.conf', has_socket_activation=True)
    facts = _build_facts([config])
    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert reports and len(reports) == 1
    _assert_socket_activation_report(reports[0].report)


def test_no_socket_activation(current_actor_context):
    config = _build_config('no_socket.conf', has_socket_activation=False)
    facts = _build_facts([config])
    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = current_actor_context.consume(Report)
    assert not reports


def test_dm_nvme(current_actor_context):
    config = _build_config('nvme.conf', has_dm_nvme_multipathing=True)
    facts = _build_facts([config])
    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert reports and len(reports) == 1
    _assert_dm_nvme_report(reports[0].report)


def test_getuid_inhibitor(current_actor_context):
    config = _build_config('getuid.conf', has_getuid=True)
    facts = _build_facts([config])
    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert reports and len(reports) == 1
    _assert_getuid_report(reports[0].report, 'getuid.conf')


def test_getuid_in_secondary(current_actor_context):
    primary = _build_config('primary.conf')
    secondary = _build_config('secondary.conf', has_getuid=True)
    facts = _build_facts([primary, secondary])
    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert reports and len(reports) == 1
    _assert_getuid_report(reports[0].report, 'secondary.conf')


def test_multiple_secondaries(current_actor_context):
    # primary: non-default bindings, no getuid
    primary = _build_config('primary.conf',
                            bindings_file='/tmp/bindings')
    # second1: overrides bindings back to default, sets non-default wwids,
    #          has getuid
    second1 = _build_config('second1.conf',
                            bindings_file='/etc/multipath/bindings',
                            wwids_file='/tmp/wwids',
                            has_getuid=True)
    # second2: overrides wwids back to default, sets non-default prkeys,
    #          no getuid
    second2 = _build_config('second2.conf',
                            wwids_file='/etc/multipath/wwids',
                            prkeys_file='/tmp/prkeys')
    # second3: has getuid only
    second3 = _build_config('second3.conf', has_getuid=True)
    facts = _build_facts([primary, second1, second2, second3])
    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    # Expect: files report (only prkeys non-default) + getuid inhibitor
    assert reports and len(reports) == 2
    _assert_files_report(reports[0].report)
    # bindings was overridden to default, wwids was overridden to default,
    # only prkeys should appear
    assert '/tmp/prkeys' in reports[0].report['summary']
    assert '/tmp/bindings' not in reports[0].report['summary']
    assert '/tmp/wwids' not in reports[0].report['summary']
    # getuid found in second1 and second3
    _assert_getuid_report(reports[1].report, 'second1.conf and second3.conf')


def test_config_dir_conflict_inhibitor(current_actor_context, monkeypatch):
    monkeypatch.setattr(mpath_conf_check, '_default_config_dir_has_conf_files', lambda: True)
    config = _build_config('custom_dir.conf',
                           config_dir='/etc/multipath/foo.d')
    facts = _build_facts([config])
    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert reports and len(reports) == 2
    _assert_config_dir_report(reports[0].report)
    _assert_config_dir_conflict_report(reports[1].report)


def test_config_dir_no_conflict(current_actor_context, monkeypatch):
    monkeypatch.setattr(mpath_conf_check, '_default_config_dir_has_conf_files', lambda: False)
    config = _build_config('custom_dir.conf',
                           config_dir='/etc/multipath/foo.d')
    facts = _build_facts([config])
    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert reports and len(reports) == 1
    _assert_config_dir_report(reports[0].report)
