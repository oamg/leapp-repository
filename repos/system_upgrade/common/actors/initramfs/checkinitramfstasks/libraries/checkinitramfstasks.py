import os
from collections import defaultdict

from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import TargetInitramfsTasks, UpgradeInitramfsTasks

DRACUT_MOD_DIR = '/usr/lib/dracut/modules.d/'
SUMMARY_DRACUT_FMT = (
    'The requested dracut modules for the initramfs are in conflict.'
    ' At least one dracut module is specified to be installed from'
    ' multiple paths. The list of conflicting dracut module names'
    ' with paths is listed below: {}'
)


def _printable_modules(conflicts):
    list_separator_fmt = '\n    - '
    for name, paths in conflicts.items():
        paths = sorted([str(i) for i in paths])
        output = ['{}{}: {}'.format(list_separator_fmt, name, paths)]
    return ''.join(output)


def _treat_path(dmodule):
    """
    In case the path is not set, set the expected path of the dracut module.
    """
    if not dmodule.module_path:
        return os.path.join(DRACUT_MOD_DIR, dmodule.name)
    return dmodule.module_path


def _detect_dracut_modules_conflicts(msgtype):
    """
    Return dict of modules with conflicting tasks

    In this case when a dracut module should be applied but different
    sources are specified. E.g.:
       include dracut modules X where,
         msg A)  X
         msg B)  X from custom path
    """
    dracut_modules = defaultdict(set)
    for msg in api.consume(msgtype):
        for dmodule in msg.include_dracut_modules:
            dracut_modules[dmodule.name].add(_treat_path(dmodule))
    return {key: val for key, val in dracut_modules.items() if len(val) > 1}


def process():
    conflicts = _detect_dracut_modules_conflicts(UpgradeInitramfsTasks)
    if conflicts:
        report = [
            reporting.Title('Conflicting requirements of dracut modules for the upgrade initramfs'),
            reporting.Summary(SUMMARY_DRACUT_FMT.format(_printable_modules(conflicts))),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.SANITY]),
            reporting.Groups([reporting.Groups.INHIBITOR]),
        ]
        reporting.create_report(report)

    conflicts = _detect_dracut_modules_conflicts(TargetInitramfsTasks)
    if conflicts:
        report = [
            reporting.Title('Conflicting requirements of dracut modules for the target initramfs'),
            reporting.Summary(SUMMARY_DRACUT_FMT.format(_printable_modules(conflicts))),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.SANITY]),
            reporting.Groups([reporting.Groups.INHIBITOR]),
        ]
        reporting.create_report(report)
