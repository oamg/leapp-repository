from leapp import reporting
from leapp.libraries.common.config import architecture
from leapp.libraries.stdlib import api
from leapp.models import SapHanaInfo

# SAP HANA Compatibility
# Requirement is SAP HANA 2.00 rev 54 which is the minimal supported revision for both RHEL 7.9 and RHEL 8.2

SAP_HANA_MINIMAL_MAJOR_VERSION = 2
SAP_HANA_RHEL8_REQUIRED_PATCH_LEVELS = ((5, 54, 0),)
SAP_HANA_MINIMAL_VERSION_STRING = 'HANA 2.0 SPS05 rev 54 or later'


def _manifest_get(manifest, key, default_value=None):
    for entry in manifest:
        if entry.key == key:
            return entry.value
    return default_value


def running_check(info):
    """ Creates a report if a running instance of SAP HANA has been detected """
    if info.running:
        reporting.create_report([
            reporting.Title('Found running SAP HANA instances'),
            reporting.Summary(
                'In order to perform a system upgrade it is necessary that all instances of SAP HANA are stopped.'
            ),
            reporting.RemediationHint('Shutdown all SAP HANA instances before you continue with the upgrade.'),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.SANITY]),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Audience('sysadmin')
        ])


def _add_hana_details(target, instance):
    """ Adds instance information into the target dictionary for creating later reports. """
    target.setdefault(instance.name, {'numbers': set(), 'path': instance.path, 'admin': instance.admin})
    target[instance.name]['numbers'].add(instance.instance_number)


def _create_detected_instances_list(details):
    """ Generates report data for detected instances in list form with details """
    result = []
    for name, meta in details.items():
        result.append(('Name: {name}\n'
                       '  Instances: {instances}\n'
                       '  Admin: {admin}\n'
                       '  Path: {path}').format(name=name,
                                                instances=', '.join(meta['numbers']),
                                                admin=meta['admin'],
                                                path=meta['path']))
    if result:
        return '- {}'.format('\n- '.join(result))
    return ''


def version1_check(info):
    """ Creates a report for SAP HANA instances running on version 1 """
    found = {}
    for instance in info.instances:
        if _manifest_get(instance.manifest, 'release') == '1.00':
            _add_hana_details(found, instance)

    if found:
        detected = _create_detected_instances_list(found)
        reporting.create_report([
            reporting.Title('Found SAP HANA 1 which is not supported with the target version of RHEL'),
            reporting.Summary(
                ('SAP HANA 1.00 is not supported with the version of RHEL you are upgrading to.\n\n'
                 'The following instances have been detected to be version 1.00:\n'
                 '{}'.format(detected))
            ),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.RemediationHint((
                'In order to upgrade RHEL, you will have to upgrade your SAP HANA 1.0 software to '
                '{supported}.'.format(supported=SAP_HANA_MINIMAL_VERSION_STRING))),
            reporting.ExternalLink(url='https://launchpad.support.sap.com/#/notes/2235581',
                                   title='SAP HANA: Supported Operating Systems'),
            reporting.Groups([reporting.Groups.SANITY]),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Audience('sysadmin')
        ])


def _major_version_check(instance):
    """ Performs the check for the major version of SAP HANA """
    release = _manifest_get(instance.manifest, 'release', '0.00')
    parts = release.split('.')

    try:
        if int(parts[0]) != SAP_HANA_MINIMAL_MAJOR_VERSION:
            api.current_logger().info('Unsupported major version {} for instance {}'.format(release, instance.name))
            return False
        return True
    except (ValueError, IndexError):
        api.current_logger().warn(
            'Failed to parse manifest release field for instance {}'.format(instance.name), exc_info=True)
        return False


def _sp_rev_patchlevel_check(instance):
    """ Checks whether this SP, REV & PatchLevel are eligible """
    number = _manifest_get(instance.manifest, 'rev-number', '000')
    if len(number) > 2 and number.isdigit():
        required_sp_levels = [r[0] for r in SAP_HANA_RHEL8_REQUIRED_PATCH_LEVELS]
        lowest_sp = min(required_sp_levels)
        highest_sp = max(required_sp_levels)
        sp = int(number[0:2].lstrip('0') or '0')
        if sp < lowest_sp:
            # Less than minimal required SP
            return False
        if sp > highest_sp:
            # Less than minimal required SP
            return True
        for requirements in SAP_HANA_RHEL8_REQUIRED_PATCH_LEVELS:
            req_sp, req_rev, req_pl = requirements
            if sp == req_sp:
                rev = int(number.lstrip('0') or '0')
                if rev < req_rev:
                    continue
                if rev == req_rev:
                    patch_level = int(_manifest_get(instance.manifest, 'rev-patchlevel', '00').lstrip('0') or '0')
                    if patch_level < req_pl:
                        continue
                return True
        return False
    # if not 'len(number) > 2 and number.isdigit()'
    api.current_logger().warn(
        'Invalid rev-number field value `{}` in manifest for instance {}'.format(number, instance.name))
    return False


def _fullfills_hana_min_version(instance):
    """ Performs a check whether the version of SAP HANA fullfills the minimal requirements for the target RHEL """
    return _major_version_check(instance) and _sp_rev_patchlevel_check(instance)


def version2_check(info):
    """ Performs all checks for SAP HANA 2 and creates a report if anything unsupported has been detected """
    found = {}
    for instance in info.instances:
        if _manifest_get(instance.manifest, 'release', None) == '1.00':
            continue
        if not _fullfills_hana_min_version(instance):
            _add_hana_details(found, instance)

    if found:
        detected = _create_detected_instances_list(found)
        reporting.create_report([
            reporting.Title('SAP HANA needs to be updated before upgrade'),
            reporting.Summary(
                ('A newer version of SAP HANA is required in order continue with the upgrade.'
                 ' {min_hana_version} is required for the target version of RHEL.\n\n'
                 'The following SAP HANA instances have been detected to be running with a lower version'
                 ' than required on the target system:\n'
                 '{detected}').format(detected=detected, min_hana_version=SAP_HANA_MINIMAL_VERSION_STRING)
            ),
            reporting.RemediationHint('Update SAP HANA at least to {}'.format(SAP_HANA_MINIMAL_VERSION_STRING)),
            reporting.ExternalLink(url='https://launchpad.support.sap.com/#/notes/2235581',
                                   title='SAP HANA: Supported Operating Systems'),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.SANITY]),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Audience('sysadmin')
        ])


def platform_check():
    """ Creates an inhibitor report in case the system is not running on x86_64 """
    if not architecture.matches_architecture(architecture.ARCH_X86_64):
        reporting.create_report([
            reporting.Title('SAP HANA upgrades are only supported on X86_64 systems'),
            reporting.Summary(
                ('Upgrades for SAP HANA are only supported on X86_64 systems.'
                 ' For more information please consult the documentation.')
            ),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.SANITY]),
            reporting.Groups([reporting.Groups.INHIBITOR]),
            reporting.Audience('sysadmin'),
            reporting.ExternalLink(
                url='https://access.redhat.com/solutions/5533441',
                title='How do I upgrade from Red Hat Enterprise Linux 7 to Red Hat Enterprise Linux 8 with SAP HANA')
        ])
        return False

    return True


def perform_check():
    """ Performs all checks for SAP HANA and will skip if the upgrade flavour is not `saphana` """

    if api.current_actor().configuration.flavour != 'saphana':
        # Do not run on non saphana upgrades
        return

    if not platform_check():
        # If this architecture is not supported, there's no sense in continuing.
        return

    info = next(api.consume(SapHanaInfo), None)
    if not info:
        return

    running_check(info)
    version1_check(info)
    version2_check(info)
