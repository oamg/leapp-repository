from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import ThirdPartyTargetPythonModules

FMT_LIST_SEPARATOR = '\n    - '
MAX_REPORTED_ITEMS = 30


def _formatted_list_output_with_max_items(input_list, sep=FMT_LIST_SEPARATOR, max_items=MAX_REPORTED_ITEMS):
    if not input_list:
        return ''

    total_count = len(input_list)
    items_to_show = input_list[:max_items]
    formatted = ['{}{}'.format(sep, item) for item in items_to_show]

    if total_count > max_items:
        formatted.append('{}... and {} more'.format(sep, total_count - max_items))

    return ''.join(formatted)


def check_third_party_target_python_modules(third_party_target_python_modules):
    """Create an inhibitor when third-party Python modules are detected."""
    target_python_version = third_party_target_python_modules.target_python.split('python')[1]
    third_party_rpms = third_party_target_python_modules.third_party_rpm_names
    third_party_modules = third_party_target_python_modules.third_party_modules

    summary = (
        'Third-party target Python modules may interfere with '
        'the upgrade process or cause unexpected behavior after the upgrade.'
    )

    if third_party_rpms:
        summary = (
            '{pre}\n\nNon-distribution RPM packages detected:{rpmlist}'
            .format(
                pre=summary,
                rpmlist=_formatted_list_output_with_max_items(third_party_rpms))
        )

    if third_party_modules:
        summary = (
            '{pre}\n\nNon-distribution modules detected (list can be incomplete):{modulelist}'
            .format(
                pre=summary,
                modulelist=_formatted_list_output_with_max_items(third_party_modules))
        )

    reporting.create_report([
        reporting.Title('Detected third-party Python modules for the target Python version'),
        reporting.Summary(summary),
        reporting.Remediation(
            hint='Remove third-party target Python {} packages before attempting the upgrade or ensure '
                 'that those modules are not interfering with distribution-provided modules.'
                 .format(target_python_version),
        ),
        reporting.Severity(reporting.Severity.HIGH)
    ])


def perform_check():
    """Perform the check for third-party Python modules."""
    third_party_target_python_modules_msg = next(api.consume(
        ThirdPartyTargetPythonModules),
        None,
    )

    if not third_party_target_python_modules_msg:
        return

    if (third_party_target_python_modules_msg.third_party_rpm_names or
       third_party_target_python_modules_msg.third_party_modules):
        check_third_party_target_python_modules(third_party_target_python_modules_msg)
