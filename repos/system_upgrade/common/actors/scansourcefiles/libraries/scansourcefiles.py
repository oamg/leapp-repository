import os

from leapp.libraries.common.config.version import get_source_major_version
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.models import FileInfo, TrackedFilesInfoSource

# TODO(pstodulk): make linter happy about this
# common -> Files supposed to be scanned on all system versions.
# '8' (etc..) -> files supposed to be scanned when particular major version of OS is used
TRACKED_FILES = {
    'common': [
        '/etc/pki/tls/openssl.cnf',
    ],
    '8': [
    ],
    '9': [
    ],
}

# TODO(pstodulk)?: introduce possibility to discover files under a dir that
# are not tracked by any rpm or a specified rpm? Currently I have only one
# use case for that in my head, so possibly it will be better to skip a generic
# solution and just introduce a new actor and msg for that (check whether
# actors not owned by our package(s) are present).


def _get_rpm_name(input_file):
    try:
        rpm_names = run(['rpm', '-qf', '--queryformat', r'%{NAME}\n', input_file], split=True)['stdout']
    except CalledProcessError:
        # is not owned by any rpm
        return ''

    if len(rpm_names) > 1:
        # this is very seatbelt; could happen for directories, but we do
        # not expect here directories specified at all. if so, we should
        # provide list instead of string
        api.current_logger().warning(
            'The {} file is owned by multiple rpms: {}.'
            .format(input_file, ', '.join(rpm_names))
        )
    return rpm_names[0]


def is_modified(input_file):
    """
    Return True if checksum has been changed (or removed).

    Ignores mode, user, type, ...
    """
    result = run(['rpm', '-Vf', '--nomtime', input_file], checked=False)
    if not result['exit_code']:
        return False
    status = result['stdout'].split()[0]
    return status == 'missing' or '5' in status


def scan_file(input_file):
    data = {
        'path': input_file,
        'exists': os.path.exists(input_file),
        'rpm_name': _get_rpm_name(input_file),
    }

    if data['rpm_name']:
        data['is_modified'] = is_modified(input_file)
    else:
        # it's not tracked by any rpm at all, so always False
        data['is_modified'] = False

    return FileInfo(**data)


def scan_files(files):
    return [scan_file(fname) for fname in files]


def process():
    files = scan_files(TRACKED_FILES['common'] + TRACKED_FILES.get(get_source_major_version(), []))
    api.produce(TrackedFilesInfoSource(files=files))
