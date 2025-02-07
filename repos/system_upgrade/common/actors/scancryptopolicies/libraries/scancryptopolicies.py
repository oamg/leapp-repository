import os

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api, run
from leapp.models import CryptoPolicyInfo, CustomCryptoPolicy, CustomCryptoPolicyModule

CRYPTO_CURRENT_STATE_FILE = '/etc/crypto-policies/state/current'
CRYPTO_POLICIES_POLICY_DIRS = ('/etc/crypto-policies/policies',
                               '/usr/share/crypto-policies/policies',)
CRYPTO_POLICIES_MODULES_DIRS = ('/etc/crypto-policies/policies/modules',
                                '/usr/share/crypto-policies/policies/modules',)


def read_current_policy(filename):
    if not os.path.exists(filename):
        # NOTE(pstodulk) just seatbelt, I do not expect the file is not present
        # skipping tests
        raise StopActorExecutionError(
                'File not found: {}'.format(filename),
                details={'details:': 'Cannot check the current set crypto policies.'}
        )
    current = 'DEFAULT'
    with open(filename) as fp:
        current = fp.read().strip()
    return current


def _get_name_from_file(filename):
    """This is just stripping the path and the extension"""
    base = os.path.basename(filename)
    return os.path.splitext(base)[0]


def find_rpm_untracked(files):
    """Check if the list of files is tracked by RPM"""
    if not files:
        return []
    try:
        res = run(['rpm', '-Vf', ] + files, split=True, checked=False)
    except OSError as err:
        error = 'Failed to invoke rpm to check untracked files: {}'.format(str(err))
        api.current_logger().error(error)
        return []

    # return only untracked files from the list
    out = []
    for filename in files:
        exp = "file {} is not owned by any package".format(filename)
        if exp in res['stdout']:
            out.append(filename)
    return out


def read_policy_dirs(dirs, obj, extension):
    """List files with given extension in given directories. Returns only the ones that are not tracked by RPM"""
    files = []
    # find all policy files
    for d in dirs:
        for filename in os.listdir(d):
            filepath = os.path.join(d, filename)
            if not os.path.isfile(filepath) or not filepath.endswith(extension):
                continue
            files.append(filepath)
    # now, check which are not tracked by RPM:
    files = find_rpm_untracked(files)
    out = []
    for filename in files:
        name = _get_name_from_file(filename)
        out.append(obj(name=name, path=filename))

    return out


def process():
    current = read_current_policy(CRYPTO_CURRENT_STATE_FILE)

    policies = read_policy_dirs(CRYPTO_POLICIES_POLICY_DIRS, CustomCryptoPolicy, ".pol")
    modules = read_policy_dirs(CRYPTO_POLICIES_MODULES_DIRS, CustomCryptoPolicyModule, ".pmod")

    api.produce(CryptoPolicyInfo(current_policy=current,
                                 custom_policies=policies,
                                 custom_modules=modules))
