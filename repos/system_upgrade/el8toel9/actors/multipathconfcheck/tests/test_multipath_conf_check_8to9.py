from leapp.models import MultipathConfFacts8to9, MultipathConfig8to9
from leapp.reporting import Report


def _assert_foreign_report(report):
    assert report['title'] == \
        'device-mapper-multipath now defaults to ignoring foreign devices'
    assert report['severity'] == 'info'


def _assert_allow_usb_report(report):
    assert report['title'] == \
        'device-mapper-multipath now defaults to ignoring USB devices'
    assert report['severity'] == 'info'


def _assert_invalid_regexes_report(report, paths_str):
    assert report['title'] == \
        'device-mapper-multipath no longer accepts "*" as a valid regular expression'
    assert report['severity'] == 'info'
    assert paths_str in report['summary']


def _build_config(pathname, config_dir, enable_foreign_exists, invalid_regexes_exist, allow_usb_exists):
    return MultipathConfig8to9(
        pathname=pathname,
        config_dir=config_dir,
        enable_foreign_exists=enable_foreign_exists,
        invalid_regexes_exist=invalid_regexes_exist,
        allow_usb_exists=allow_usb_exists,
    )


def _build_facts(confs):
    return MultipathConfFacts8to9(configs=confs)


def test_need_everything(current_actor_context):
    config = _build_config('need_everything.conf', None, False, True, False)
    facts = _build_facts([config])
    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert reports and len(reports) == 3
    _assert_foreign_report(reports[0].report)
    _assert_allow_usb_report(reports[1].report)
    _assert_invalid_regexes_report(reports[2].report, 'need_everything.conf')


def test_need_nothing(current_actor_context):
    config = _build_config('need_nothing.conf', '/etc/multipath/conf.d', True, False, True)
    facts = _build_facts([config])
    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = current_actor_context.consume(Report)
    assert not reports


def test_need_foreign(current_actor_context):
    config = _build_config('need_foreign.conf', None, False, False, True)
    facts = _build_facts([config])
    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert reports and len(reports) == 1
    _assert_foreign_report(reports[0].report)


def test_need_allos_usb(current_actor_context):
    config = _build_config('need_allow_usb.conf', None, True, False, False)
    facts = _build_facts([config])
    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert reports and len(reports) == 1
    _assert_allow_usb_report(reports[0].report)


def test_invalid_regexes(current_actor_context):
    config1 = _build_config('invalid_regexes1.conf', None, True, True, True)
    config2 = _build_config('no_invalid_regexes.conf', None, True, False, True)
    config3 = _build_config('invalid_regexes2.conf', None, True, True, True)
    facts = _build_facts([config1, config2, config3])
    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert reports and len(reports) == 1
    _assert_invalid_regexes_report(reports[0].report, 'invalid_regexes1.conf and invalid_regexes2.conf')


def test_not_in_main_conf(current_actor_context):
    main_conf = _build_config('main.conf', '/etc/multipath/conf.d', False, True, False)
    other_conf = _build_config('other.conf', None, True, False, True)
    facts = _build_facts([main_conf, other_conf])
    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert reports and len(reports) == 1
    _assert_invalid_regexes_report(reports[0].report, 'main.conf')


def test_in_main_conf(current_actor_context):
    main_conf = _build_config('main.conf', '/etc/multipath/conf.d', True, True, True)
    other_conf = _build_config('other.conf', None, False, False, False)
    next_conf = _build_config('next.conf', None, False, True, False)
    last_conf = _build_config('last.conf', None, False, True, False)
    facts = _build_facts([main_conf, other_conf, next_conf, last_conf])
    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert reports and len(reports) == 1
    _assert_invalid_regexes_report(reports[0].report, 'main.conf, next.conf and last.conf')


def test_in_none_conf(current_actor_context):
    main_conf = _build_config('main.conf', '/etc/multipath/conf.d', False, False, False)
    other_conf = _build_config('other.conf', None, False, False, False)
    facts = _build_facts([main_conf, other_conf])
    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert reports and len(reports) == 2
    _assert_foreign_report(reports[0].report)
    _assert_allow_usb_report(reports[1].report)


def test_mixed_conf(current_actor_context):
    main_conf = _build_config('main.conf', None, True, False, False)
    next_conf = _build_config('next.conf', None, False, True, False)
    last_conf = _build_config('last.conf', None, True, False, False)
    facts = _build_facts([main_conf, next_conf, last_conf])
    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert reports and len(reports) == 2
    _assert_allow_usb_report(reports[0].report)
    _assert_invalid_regexes_report(reports[1].report, 'next.conf')
