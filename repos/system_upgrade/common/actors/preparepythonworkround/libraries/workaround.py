import os
import shutil
import sys

from leapp.libraries.common.utils import makedirs
from leapp.libraries.stdlib import api

LEAPP_HOME = '/root/tmp_leapp_py3'


def _get_python_dirname():
    # NOTE: I thought about the static value: python2.7 for el7, python3.6 for
    # el8; but in the end I've ratcher switched to this generic solution.
    return 'python{}.{}'.format(sys.version_info.major, sys.version_info.minor)


def _get_orig_leapp_path():
    return os.path.join('/usr/lib', _get_python_dirname(), 'site-packages/leapp')


def apply_python3_workaround():
    py3_leapp = os.path.join(LEAPP_HOME, 'leapp3')
    if os.path.exists(LEAPP_HOME):
        try:
            shutil.rmtree(LEAPP_HOME)
        except OSError as e:
            api.current_logger().error('Could not remove {} directory: {}'.format(LEAPP_HOME, str(e)))

    makedirs(LEAPP_HOME)
    leapp_lib_symlink_path = os.path.join(LEAPP_HOME, 'leapp')
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
