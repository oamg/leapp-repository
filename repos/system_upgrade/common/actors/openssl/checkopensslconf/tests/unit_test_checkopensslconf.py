import pytest

from leapp import reporting
from leapp.libraries.actor import checkopensslconf
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, FileInfo, RPM, TrackedFilesInfoSource

_DUMP_PKG_NAMES = ['random', 'pkgs', 'openssl-ibmca-nope', 'ibmca', 'nope-openssl-ibmca']
_SSL_CONF = checkopensslconf.DEFAULT_OPENSSL_CONF


def _msg_pkgs(pkgnames):
    rpms = []
    for pname in pkgnames:
        rpms.append(RPM(
            name=pname,
            epoch='0',
            version='1.0',
            release='1',
            arch='noarch',
            pgpsig='RSA/SHA256, Mon 01 Jan 1970 00:00:00 AM -03, Key ID 199e2f91fd431d51',
            packager='Red Hat, Inc. (auxiliary key 2) <security@redhat.com>'

        ))
    return DistributionSignedRPM(items=rpms)


@pytest.mark.parametrize('arch,pkgnames,ibmca_report', (
    (architecture.ARCH_S390X, [], False),
    (architecture.ARCH_S390X, _DUMP_PKG_NAMES, False),
    (architecture.ARCH_S390X, ['openssl-ibmca'], True),
    (architecture.ARCH_S390X, _DUMP_PKG_NAMES + ['openssl-ibmca'], True),
    (architecture.ARCH_S390X, ['openssl-ibmca'] + _DUMP_PKG_NAMES, True),

    # stay false for non-IBM-z arch - invalid scenario basically
    (architecture.ARCH_X86_64, ['openssl-ibmca'], False),
    (architecture.ARCH_PPC64LE, ['openssl-ibmca'], False),
    (architecture.ARCH_ARM64, ['openssl-ibmca'], False),

))
@pytest.mark.parametrize('src_maj_ver', ('7', '8', '9'))
def test_check_ibmca(monkeypatch, src_maj_ver, arch, pkgnames, ibmca_report):
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        arch=arch,
        msgs=[_msg_pkgs(pkgnames)],
        src_ver='{}.6'.format(src_maj_ver),
        dst_ver='{}.0'.format(int(src_maj_ver) + 1)
    ))
    checkopensslconf.check_ibmca()

    if not ibmca_report:
        assert not reporting.create_report.called, 'IBMCA report created when it should not.'
    else:
        assert reporting.create_report.called, 'IBMCA report has not been created.'


def _msg_files(fnames_changed, fnames_untouched):
    res = []
    for fname in fnames_changed:
        res.append(FileInfo(
            path=fname,
            exists=True,
            is_modified=True
        ))

    for fname in fnames_untouched:
        res.append(FileInfo(
            path=fname,
            exists=True,
            is_modified=False
        ))

    return TrackedFilesInfoSource(files=res)


# NOTE(pstodulk): Ignoring situation when _SSL_CONF is missing (modified, do not exists).
# It's not a valid scenario actually, as this file just must exists on the system to
# consider it in a supported state.
@pytest.mark.parametrize('msg,openssl_report', (
    # matrix focused on openssl reports only (positive)
    (_msg_files([], []), False),
    (_msg_files([_SSL_CONF], []), True),
    (_msg_files(['what/ever', _SSL_CONF, 'something'], []), True),
    (_msg_files(['what/ever'], [_SSL_CONF]), False),
))
@pytest.mark.parametrize('src_maj_ver', ('7', '8', '9'))
def test_check_openssl(monkeypatch, src_maj_ver, msg, openssl_report):
    monkeypatch.setattr(reporting, "create_report", create_report_mocked())
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(
        msgs=[msg],
        src_ver='{}.6'.format(src_maj_ver),
        dst_ver='{}.0'.format(int(src_maj_ver) + 1)
    ))
    checkopensslconf.process()

    if not openssl_report:
        assert not reporting.create_report.called, 'OpenSSL report created when it should not.'
    else:
        assert reporting.create_report.called, 'OpenSSL report has not been created.'
