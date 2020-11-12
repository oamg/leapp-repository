from leapp.models import MultipathConfFacts, MultipathConfig, \
        MultipathConfigOption
from leapp.reporting import Report
from leapp.snactor.fixture import current_actor_context


def _assert_default_checker_report(report, pathname):
    assert report['title'] == \
        'Unsupported device-mapper-multipath configuration'
    assert report['severity'] == 'high'
    assert 'inhibitor' in report['groups']
    assert pathname in report['summary']


def _assert_default_detect_report(report, pathname):
    assert report['title'] == \
        'device-mapper-multipath now defaults to detecting settings'
    assert report['severity'] == 'medium'
    assert pathname in report['summary']


def _assert_reassign_maps(report, pathname):
    assert report['title'] == \
        'device-mapper-multipath now disables reassign_maps by default'
    assert report['severity'] == 'medium'
    assert pathname in report['summary']


def test_config_all_bad(current_actor_context):
    config = MultipathConfig(
            pathname='all_bad.conf', default_path_checker='directio',
            reassign_maps=True, default_detect_checker=False,
            default_detect_prio=False, default_retain_hwhandler=False)
    facts = MultipathConfFacts(configs=[config])

    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert reports and len(reports) == 3
    _assert_default_checker_report(reports[0].report, 'all_bad.conf')
    _assert_default_detect_report(reports[1].report, 'all_bad.conf')
    _assert_reassign_maps(reports[2].report, 'all_bad.conf')


def test_config_all_good(current_actor_context):
    config = MultipathConfig(
            pathname='all_good.conf', default_path_checker='tur',
            reassign_maps=False, default_detect_checker=True,
            default_detect_prio=True, default_retain_hwhandler=True)
    facts = MultipathConfFacts(configs=[config])

    current_actor_context.feed(facts)
    current_actor_context.run()
    assert not current_actor_context.consume(Report)


def test_config_unimportant(current_actor_context):
    option = MultipathConfigOption(name='path_checker', value='rdac')
    config = MultipathConfig(
            pathname='unimportant.conf', hw_str_match_exists=True,
            ignore_new_boot_devs_exists=True, new_bindings_in_boot_exists=True,
            unpriv_sgio_exists=True, detect_path_checker_exists=True,
            overrides_hwhandler_exists=True, overrides_pg_timeout_exists=True,
            queue_if_no_path_exists=True, all_devs_section_exists=True,
            all_devs_options=[option])
    facts = MultipathConfFacts(configs=[config])

    current_actor_context.feed(facts)
    current_actor_context.run()
    assert not current_actor_context.consume(Report)


def test_bad_then_good(current_actor_context):
    bad_config = MultipathConfig(
            pathname='all_bad.conf', default_path_checker='directio',
            reassign_maps=True, default_detect_checker=False,
            default_detect_prio=False, default_retain_hwhandler=False)
    good_config = MultipathConfig(
            pathname='all_good.conf', default_path_checker='tur',
            reassign_maps=False, default_detect_checker=True,
            default_detect_prio=True, default_retain_hwhandler=True)
    facts = MultipathConfFacts(configs=[bad_config, good_config])

    current_actor_context.feed(facts)
    current_actor_context.run()
    assert not current_actor_context.consume(Report)


def test_good_then_bad(current_actor_context):
    good_config = MultipathConfig(
            pathname='all_good.conf', default_path_checker='tur',
            reassign_maps=False, default_detect_checker=True,
            default_detect_prio=True, default_retain_hwhandler=True)
    bad_config = MultipathConfig(
            pathname='all_bad.conf', default_path_checker='directio',
            reassign_maps=True, default_detect_checker=False,
            default_detect_prio=False, default_retain_hwhandler=False)
    facts = MultipathConfFacts(configs=[good_config, bad_config])

    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert reports and len(reports) == 3
    _assert_default_checker_report(reports[0].report, 'all_bad.conf')
    _assert_default_detect_report(reports[1].report, 'all_bad.conf')
    _assert_reassign_maps(reports[2].report, 'all_bad.conf')


def test_bad_then_nothing(current_actor_context):
    bad_config = MultipathConfig(
            pathname='all_bad.conf', default_path_checker='directio',
            reassign_maps=True, default_detect_checker=False,
            default_detect_prio=False, default_retain_hwhandler=False)
    none_config = MultipathConfig(pathname='none.conf')
    facts = MultipathConfFacts(configs=[bad_config, none_config])

    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert reports and len(reports) == 3
    _assert_default_checker_report(reports[0].report, 'all_bad.conf')
    _assert_default_detect_report(reports[1].report, 'all_bad.conf')
    _assert_reassign_maps(reports[2].report, 'all_bad.conf')


def test_nothing_then_bad(current_actor_context):
    bad_config = MultipathConfig(
            pathname='all_bad.conf', default_path_checker='directio',
            reassign_maps=True, default_detect_checker=False,
            default_detect_prio=False, default_retain_hwhandler=False)
    none_config = MultipathConfig(pathname='none.conf')
    facts = MultipathConfFacts(configs=[none_config, bad_config])

    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert reports and len(reports) == 3
    _assert_default_checker_report(reports[0].report, 'all_bad.conf')
    _assert_default_detect_report(reports[1].report, 'all_bad.conf')
    _assert_reassign_maps(reports[2].report, 'all_bad.conf')


def test_only_bad_checker(current_actor_context):
    bad_checker_config = MultipathConfig(
            pathname='bad_checker.conf', default_path_checker='rdac',
            default_retain_hwhandler=True)
    facts = MultipathConfFacts(configs=[bad_checker_config])

    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert reports and len(reports) == 1
    _assert_default_checker_report(reports[0].report, 'bad_checker.conf')


def test_only_bad_detect(current_actor_context):
    bad_detect_config = MultipathConfig(
            pathname='bad_detect.conf', default_detect_prio=True,
            default_detect_checker=False)
    facts = MultipathConfFacts(configs=[bad_detect_config])

    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert reports and len(reports) == 1
    _assert_default_detect_report(reports[0].report, 'bad_detect.conf')


def test_only_bad_reassign(current_actor_context):
    bad_reassign_config = MultipathConfig(
            pathname='bad_reassign.conf', reassign_maps=True)
    facts = MultipathConfFacts(configs=[bad_reassign_config])

    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert reports and len(reports) == 1
    _assert_reassign_maps(reports[0].report, 'bad_reassign.conf')


def test_different_files(current_actor_context):
    bad_detect_checker_config = MultipathConfig(
            pathname='bad_detect_checker.conf', default_detect_checker=False)
    bad_detect_prio_config = MultipathConfig(
            pathname='bad_detect_prio.conf', default_detect_prio=False)
    bad_retain_hwhandler_config = MultipathConfig(
            pathname='bad_retain_hwhandler.conf',
            default_retain_hwhandler=False)
    facts = MultipathConfFacts(
            configs=[bad_detect_checker_config, bad_detect_prio_config,
                     bad_retain_hwhandler_config])

    current_actor_context.feed(facts)
    current_actor_context.run()
    reports = list(current_actor_context.consume(Report))
    assert reports and len(reports) == 1
    _assert_default_detect_report(
            reports[0].report,
            'bad_detect_checker.conf, bad_detect_prio.conf and '
            'bad_retain_hwhandler.conf')
