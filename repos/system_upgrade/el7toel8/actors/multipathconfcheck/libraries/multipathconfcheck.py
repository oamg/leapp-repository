from leapp.reporting import create_report
from leapp import reporting


def _merge_configs(configs):
    options = {'default_path_checker': None, 'detect_prio': None,
               'detect_path_checker': None, 'reassign_maps': None,
               'retain_attached_hw_handler': None}
    for config in configs:
        if config.default_path_checker is not None:
            options['default_path_checker'] = (config.default_path_checker,
                                               config.pathname)

        if config.reassign_maps is not None:
            options['reassign_maps'] = (config.reassign_maps, config.pathname)

        if config.default_detect_checker is not None:
            options['detect_path_checker'] = (config.default_detect_checker,
                                              config.pathname)

        if config.default_detect_prio is not None:
            options['detect_prio'] = (config.default_detect_prio,
                                      config.pathname)

        if config.default_retain_hwhandler is not None:
            options['retain_attached_hw_handler'] = (config.default_retain_hwhandler, config.pathname)
    return options


def _check_default_path_checker(options):
    if not options['default_path_checker']:
        return
    value, pathname = options['default_path_checker']
    if value == 'tur':
        return
    create_report([
        reporting.Title(
            'Unsupported device-mapper-multipath configuration'
        ),
        reporting.Summary(
            'device-mapper-multipath has changed the default path_checker '
            'from "directio" to "tur" in RHEL-8. Further, changing the '
            'default path_checker can cause issues with built-in device '
            'configurations in RHEL-8. Please remove the "path_checker" '
            'option from the defaults section of {}, and add it to the '
            'device configuration of any devices that need it.'.
            format(pathname)
        ),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.SERVICES, reporting.Groups.INHIBITOR]),
        reporting.RelatedResource('package', 'device-mapper-multipath'),
        reporting.RelatedResource('file', pathname),
        reporting.Remediation(
            hint='Please remove the "path_checker {}" option from the '
            'defaults section of {}, and add it to the device configuration '
            'of any devices that need it.'.format(value, pathname)
        )
    ])


def _create_paths_str(paths):
    if len(paths) < 2:
        return paths[0]
    return '{} and {}'.format(', '.join(paths[0:-1]), paths[-1])


def _check_default_detection(options):
    bad = []
    for keyword in ('detect_path_checker', 'detect_prio',
                    'retain_attached_hw_handler'):
        if options[keyword] and not options[keyword][0] and \
                options[keyword][1] not in bad:
            bad.append(options[keyword][1])
    if bad == []:
        return
    paths = _create_paths_str(bad)
    create_report([
        reporting.Title(
            'device-mapper-multipath now defaults to detecting settings'
        ),
        reporting.Summary(
            'In RHEL-8, the default value for the "detect_path_checker", '
            '"detect_prio" and "retain_attached_hw_handler" options has '
            'changed to "yes". Further, changing these default values can '
            'cause issues with the built-in device configurations in RHEL-8. '
            'They will be commented out in the defaults section of all '
            'multipath config files. This is unlikely to cause any issues '
            'with existing configurations. If it does, please move these '
            'options from the defaults sections of {} to the device '
            'configuration sections of any devices that need them.'.
            format(paths)
        ),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.RelatedResource('package', 'device-mapper-multipath')
    ])


def _check_reassign_maps(options):
    if not options['reassign_maps']:
        return
    value, pathname = options['reassign_maps']
    if not value:
        return
    create_report([
        reporting.Title(
            'device-mapper-multipath now disables reassign_maps by default'
        ),
        reporting.Summary(
            'In RHEL-8, the default value for "reassign_maps" has been '
            'changed to "no", and it is not recommended to enable it in any '
            'configuration going forward. This option will be commented out '
            'in {}.'.format(pathname)
        ),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.RelatedResource('package', 'device-mapper-multipath')
    ])


def check_configs(facts):
    options = _merge_configs(facts.configs)
    _check_default_path_checker(options)
    _check_default_detection(options)
    _check_reassign_maps(options)
