import os

from leapp.libraries.common.utils import makedirs

LEAPP_HOME = '/root/tmp_leapp_py3'


def apply_python3_workaround():
    py3_leapp = os.path.join(LEAPP_HOME, 'leapp3')
    makedirs(LEAPP_HOME)
    leapp_lib_symlink_path = os.path.join(LEAPP_HOME, 'leapp')
    if not os.path.exists(leapp_lib_symlink_path):
        os.symlink('/usr/lib/python2.7/site-packages/leapp', leapp_lib_symlink_path)
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
