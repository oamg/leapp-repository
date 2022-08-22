from leapp import reporting
from leapp.reporting import create_report


def _report_foreign():
    create_report([
        reporting.Title(
            'device-mapper-multipath now defaults to ignoring foreign devices'
        ),
        reporting.Summary(
            'In RHEL-9, the default value for the "enable_foreign" option has '
            'changed to "NONE". This means that multipath will no longer list '
            'devices that are not managed by device-mapper. In order to retain '
            'the default RHEL-8 behavior of listing foreign multipath devices, '
            '\'enable_foreign ""\' will be added to the defaults section of '
            '"/etc/multipath.conf". If you wish to change to the default '
            'RHEL-9 behavior, please remove this line. This option only '
            'effects the devices that multipath lists. It has no impact on '
            'what devices are managed.'),
        reporting.Severity(reporting.Severity.INFO),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.RelatedResource('package', 'device-mapper-multipath')
    ])


def _report_allow_usb():
    create_report([
        reporting.Title(
            'device-mapper-multipath now defaults to ignoring USB devices'
        ),
        reporting.Summary(
            'In RHEL-9, the default multipath configuration has changed to '
            'ignore USB devices. A new config option, "allow_usb_devices" has '
            'been added to control this.  In order to retain the RHEL-8 '
            'behavior of treating USB devices like other block devices. '
            '"allow_usb_devices yes" will be added to the defaults section '
            'of "/etc/multipath.conf". If you wish to change to the default '
            'RHEL-9 behavior, please remove this line.'),
        reporting.Severity(reporting.Severity.INFO),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.RelatedResource('package', 'device-mapper-multipath')
    ])


def _create_paths_str(paths):
    if len(paths) < 2:
        return paths[0]
    return '{} and {}'.format(', '.join(paths[0:-1]), paths[-1])


def _report_invalid_regexes(paths):
    paths_str = _create_paths_str(paths)
    create_report([
        reporting.Title(
            'device-mapper-multipath no longer accepts "*" as a valid regular expression'
        ),
        reporting.Summary(
            'Some options in device-mapper-multipath configuration files '
            'have values that are regular expressions. In RHEL-8, if such an '
            'option had a value of "*", multipath would internally convert it '
            'to ".*". In RHEL-9, values of "*" are no longer accepted. '
            'These regular expression values have been found in {}. They '
            'will be converted to ".*"'.format(paths_str)),
        reporting.Severity(reporting.Severity.INFO),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.RelatedResource('package', 'device-mapper-multipath')
    ])


def check_configs(facts):
    need_foreign = not any(x for x in facts.configs if x.enable_foreign_exists)
    need_allow_usb = not any(x for x in facts.configs if x.allow_usb_exists)
    invalid_regexes = [x.pathname for x in facts.configs if x.invalid_regexes_exist]

    if need_foreign:
        _report_foreign()
    if need_allow_usb:
        _report_allow_usb()
    if invalid_regexes:
        _report_invalid_regexes(invalid_regexes)
