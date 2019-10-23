import copy
import os
import os.path as ph
import random
import shutil
import string
import tempfile

import pytest

from leapp.libraries.stdlib import run

CONFS = {'nopass': ['nssdb-nopass', 'User-Cert', None],
         'pass': ['nssdb', 'User-Cert', 'nssdb/pin.txt']}


def generate_noise(filename, length=512):
    out = ''.join([random.choice(string.ascii_letters) for _ in range(length)])
    with open(filename, 'w') as f:
        f.write(out.encode())


@pytest.fixture(scope='function')
def mock(request):
    confs = copy.deepcopy(CONFS)
    nssdb_files = None

    pki_dir = tempfile.mkdtemp('pki')

    noise_file = os.path.join(pki_dir, 'noise.txt')
    generate_noise(noise_file)
    noise = ['-z', noise_file]

    ca_name = 'CA'

    for name, conf in confs.items():
        loc, cert, pin_file = conf

        d = os.path.join(pki_dir, loc)
        os.mkdir(d)
        confs[name][0] = str(d)
        db = ['-d', str(d)]

        if pin_file:
            pin_file_loc = ph.join(pki_dir, pin_file)
            with open(pin_file_loc, 'w') as f:
                f.write('securepw123')
            pin = ['-f', pin_file_loc]
            confs[name][2] = str(pin_file_loc)
        else:
            pin = []

        run(['certutil', '-N'] + db + (pin or ['--empty-password']))
        run(['certutil', '-S', '-m', '1001', '-n', ca_name, '-t', 'CT,C,C',
             '-x', '-s', 'CN=example.com,O=test'] + db + noise + pin)
        run(['certutil', '-S', '-m', '1002', '-n', cert, '-t', 'u,u,u',
             '-c', ca_name, '-s', 'CN=user.example.com,O=test'] + db + noise + pin)

        nssdb_files = ['cert8.db', 'key3.db'] if ph.exists(ph.join(d, 'cert8.db')) else ['cert9.db', 'key4.db']

    def fin():
        shutil.rmtree(pki_dir)

    request.addfinalizer(fin)

    # Because we cannot simply parametrize tests with this function's return value,
    # the tests will be parametrized with CONFS but will actually use this function's
    # confs of return value instead. And this line below just asserts we have at least
    # the keys the same.
    assert list(confs) == list(CONFS)

    return (confs, nssdb_files)
