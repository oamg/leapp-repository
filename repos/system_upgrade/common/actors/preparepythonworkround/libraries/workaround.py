import os
import sys

from leapp.libraries.common.utils import makedirs

LEAPP_HOME = '/root/tmp_leapp_py3'


def _get_python_dirname():
    # NOTE: I thought about the static value: python2.7 for el7, python3.6 for
    # el8; but in the end I've ratcher switched to this generic solution.
    return 'python{}.{}'.format(sys.version_info.major, sys.version_info.minor)


def _get_orig_leapp_path():
    return os.path.join('/usr/lib', _get_python_dirname(), 'site-packages/leapp')


def apply_python3_workaround():
    py3_leapp = os.path.join(LEAPP_HOME, 'leapp3')
    makedirs(LEAPP_HOME)
    leapp_lib_symlink_path = os.path.join(LEAPP_HOME, 'leapp')
    if not os.path.exists(leapp_lib_symlink_path):
        os.symlink(_get_orig_leapp_path(), leapp_lib_symlink_path)
    with open(py3_leapp, 'w') as f:
        f_content = [
            '#!/usr/bin/python3',
            'import sys',
            'sys.path.append(\'{}\')'.format(LEAPP_HOME),
            '',
            'import leapp.cli',
            'sys.exit(leapp.cli.main())',
        ]
        f.write('{}\n\n'.format('\n'.join(f_content)))
    os.chmod(py3_leapp, 0o770)
