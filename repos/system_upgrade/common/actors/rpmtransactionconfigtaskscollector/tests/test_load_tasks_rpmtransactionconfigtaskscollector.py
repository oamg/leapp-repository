import logging

from leapp.libraries.actor.rpmtransactionconfigtaskscollector import load_tasks, load_tasks_file
from leapp.libraries.stdlib import api
from leapp.models import InstalledRedHatSignedRPM, RPM

RH_PACKAGER = 'Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>'


def test_load_tasks(tmpdir, monkeypatch):

    def consume_signed_rpms_mocked(*models):
        installed = [
            RPM(name='c', version='0.1', release='1.sm01', epoch='1', packager=RH_PACKAGER, arch='noarch',
                pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51')
            ]
        yield InstalledRedHatSignedRPM(items=installed)

    monkeypatch.setattr(api, "consume", consume_signed_rpms_mocked)

    tmpdir.join('to_install').write('a\n b\n  c \n\n\nc\na\nc\nb')
    tmpdir.join('to_keep').write('a\n b\n  c \n\n\nc\na\nc\nb')
    tmpdir.join('to_remove').write('a\n b\n  c \n\n\nc\na\nc\nb')
    m = load_tasks(tmpdir.strpath, logging)
    # c is not going to be in "to_install" as it is already installed
    assert set(m.to_install) == set(['a', 'b'])
    assert set(m.to_keep) == set(['a', 'b', 'c'])
    assert set(m.to_remove) == set(['a', 'b', 'c'])


def test_load_tasks_file(tmpdir):
    f = tmpdir.join('to_install')
    f.write('a\n b\n  c \n\n\nc\na\nc\nb')
    assert set(load_tasks_file(f.strpath, logging)) == set(['a', 'b', 'c'])
    f = tmpdir.join('to_keep')
    f.write(' ')
    assert set(load_tasks_file(f.strpath, logging)) == set([])
