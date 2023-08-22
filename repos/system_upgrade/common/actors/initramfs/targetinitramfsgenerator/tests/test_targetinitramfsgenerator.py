import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import targetinitramfsgenerator
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.utils.deprecation import suppress_deprecation

from leapp.models import (    # isort:skip
    InitrdIncludes,    # deprecated
    DracutModule, KernelModule, InstalledTargetKernelInfo, TargetInitramfsTasks)

FILES = ['/file1', '/file2', '/dir/subdir/subsubdir/file3', '/file4', '/file5']
MODULES = [
    ('moduleA', None),
    ('moduleB', None),
    ('moduleC', '/some/path/moduleC'),
    ('moduleD', '/some/path/moduleD'),
]
KERNEL_VERSION = '4.18.0'
NO_INCLUDE_MSG = 'No additional files or modules required to add into the target initramfs.'


def raise_call_error(args=None):
    raise CalledProcessError(message='A Leapp Command Error occurred.',
                             command=args,
                             result={
                                 'signal': None,
                                 'exit_code': 1,
                                 'pid': 0,
                                 'stdout': 'fake',
                                 'stderr': 'fake'
                             })


class RunMocked(object):

    def __init__(self, raise_err=False):
        self.called = 0
        self.args = []
        self.raise_err = raise_err

    def __call__(self, args):
        self.called += 1
        self.args = args
        if self.raise_err:
            raise_call_error(args)


def _ensure_list(data):
    return data if isinstance(data, list) else [data]


def gen_TIT(dracut_modules, kernel_modules, files):
    files = _ensure_list(files)

    dracut_modules = [DracutModule(name=i[0], module_path=i[1]) for i in _ensure_list(dracut_modules)]
    kernel_modules = [KernelModule(name=i[0], module_path=i[1]) for i in _ensure_list(kernel_modules)]

    return TargetInitramfsTasks(
        include_files=files,
        include_dracut_modules=dracut_modules,
        include_kernel_modules=kernel_modules,
    )


@suppress_deprecation(InitrdIncludes)
def gen_InitrdIncludes(files):
    return InitrdIncludes(files=_ensure_list(files))


def test_no_includes(monkeypatch):
    run_mocked = RunMocked()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[]))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(targetinitramfsgenerator, 'run', run_mocked)

    targetinitramfsgenerator.process()
    assert NO_INCLUDE_MSG in api.current_logger.dbgmsg
    assert not run_mocked.called


TEST_CASES = [
    [
        gen_InitrdIncludes(FILES[0:3]),
        gen_InitrdIncludes(FILES[3:]),
    ],
    [
        gen_TIT([], [], FILES[0:3]),
        gen_TIT([], [], FILES[3:]),
    ],
    [
        gen_InitrdIncludes(FILES[0:3]),
        gen_TIT([], [], FILES[3:]),
    ],
]


@pytest.mark.parametrize('msgs', TEST_CASES)
def test_no_kernel_version(monkeypatch, msgs):
    run_mocked = RunMocked()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(targetinitramfsgenerator, 'run', run_mocked)
    # FIXME
    monkeypatch.setattr(targetinitramfsgenerator, '_copy_modules', lambda *_: None)

    with pytest.raises(StopActorExecutionError) as e:
        targetinitramfsgenerator.process()
    assert 'Cannot get version of the installed RHEL-8 kernel' in str(e)
    assert not run_mocked.called


def mk_kernel_info(kernel_ver):
    kernel_info = InstalledTargetKernelInfo(pkg_nevra='nevra',
                                            kernel_img_path='vmlinuz',
                                            uname_r=kernel_ver,
                                            initramfs_path='initramfs')
    return kernel_info


@pytest.mark.parametrize('msgs', TEST_CASES)
def test_dracut_fail(monkeypatch, msgs):
    run_mocked = RunMocked(raise_err=True)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'current_actor',
                        CurrentActorMocked(msgs=msgs + [mk_kernel_info(KERNEL_VERSION)]))
    monkeypatch.setattr(targetinitramfsgenerator, 'run', run_mocked)
    # FIXME
    monkeypatch.setattr(targetinitramfsgenerator, '_copy_modules', lambda *_: None)

    with pytest.raises(StopActorExecutionError) as e:
        targetinitramfsgenerator.process()
    assert 'Cannot regenerate dracut image' in str(e)
    assert run_mocked.called


@pytest.mark.parametrize(
    'msgs,files,dracut_modules,kernel_modules',
    [
        # deprecated set
        ([gen_InitrdIncludes(FILES[0])], FILES[0:1], [], []),
        ([gen_InitrdIncludes(FILES)], FILES, [], []),
        ([gen_InitrdIncludes(FILES[0:3]), gen_InitrdIncludes(FILES[3:])], FILES, [], []),
        ([gen_InitrdIncludes(FILES[0:3]), gen_InitrdIncludes(FILES)], FILES, [], []),

        # new set for files only
        ([gen_TIT([], [], FILES[0])], FILES[0:1], [], []),
        ([gen_TIT([], [], FILES)], FILES, [], []),
        ([gen_TIT([], [], FILES[0:3]), gen_TIT([], [], FILES[3:])], FILES, [], []),
        ([gen_TIT([], [], FILES[0:3]), gen_TIT([], [], FILES)], FILES, [], []),

        # deprecated and new msgs for files only
        ([gen_InitrdIncludes(FILES[0:3]), gen_TIT([], [], FILES[3:])], FILES, [], []),

        # dracut modules only
        ([gen_TIT(MODULES[0], [], [])], [], MODULES[0:1], []),
        ([gen_TIT(MODULES, [], [])], [], MODULES, []),
        ([gen_TIT(MODULES[0:3], [], []), gen_TIT(MODULES[3], [], [])], [], MODULES, []),

        # kernel modules only
        ([gen_TIT([], MODULES[0], [])], [], [], MODULES[0:1]),
        ([gen_TIT([], MODULES, [])], [], [], MODULES),
        ([gen_TIT([], MODULES[0:3], []), gen_TIT([], MODULES[3], [])], [], [], MODULES),

        # modules only - duplicates; see notes in the library
        ([gen_TIT(MODULES[0:3], [], []), gen_TIT(MODULES, [], [])], [], MODULES, []),
        ([gen_TIT([], MODULES[0:3], []), gen_TIT([], MODULES, [])], [], [], MODULES),

        # modules + files (new only)
        ([gen_TIT(MODULES, [], FILES)], FILES, MODULES, []),
        ([gen_TIT([], MODULES, FILES)], FILES, [], MODULES),

        ([gen_TIT(MODULES[0:3], [], FILES[0:3]), gen_TIT(MODULES[3:], [], FILES[3:])], FILES, MODULES, []),
        ([gen_TIT([], MODULES[0:3], FILES[0:3]), gen_TIT([], MODULES[3:], FILES[3:])], FILES, [], MODULES),

        ([gen_TIT(MODULES, [], []), gen_TIT([], [], FILES)], FILES, MODULES, []),
        ([gen_TIT([], MODULES, []), gen_TIT([], [], FILES)], FILES, [], MODULES),

        # kernel + dracut modules
        (
            [
                gen_TIT(MODULES[0:3], MODULES[0:3], FILES[0:3]),
                gen_TIT(MODULES[3:], MODULES[3:], FILES[3:])
            ],
            FILES, MODULES, MODULES
        ),

        # modules + files with deprecated msgs
        ([gen_TIT(MODULES, [], []), gen_InitrdIncludes(FILES)], FILES, MODULES, []),
        ([gen_TIT([], MODULES, []), gen_InitrdIncludes(FILES)], FILES, [], MODULES),

        ([gen_TIT(MODULES, [], FILES[0:3]), gen_InitrdIncludes(FILES[3:])], FILES, MODULES, []),
        ([gen_TIT([], MODULES, FILES[0:3]), gen_InitrdIncludes(FILES[3:])], FILES, [], MODULES),
    ])
def test_flawless(monkeypatch, msgs, files, dracut_modules, kernel_modules):
    _msgs = msgs + [mk_kernel_info(KERNEL_VERSION)]
    run_mocked = RunMocked()
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=_msgs))
    monkeypatch.setattr(targetinitramfsgenerator, 'run', run_mocked)
    # FIXME
    monkeypatch.setattr(targetinitramfsgenerator, '_copy_modules', lambda *_: None)

    targetinitramfsgenerator.process()
    assert run_mocked.called

    # check files
    if files:
        assert '--install' in run_mocked.args
        arg = run_mocked.args[run_mocked.args.index('--install') + 1]
        for f in files:
            assert f in arg
    else:
        assert '--install' not in run_mocked.args

    # check dracut modules
    if dracut_modules:
        assert '--add' in run_mocked.args
        arg = run_mocked.args[run_mocked.args.index('--add') + 1]
        for m in dracut_modules:
            assert m[0] in arg
    else:
        assert '--add' not in run_mocked.args

    # check kernel modules
    if kernel_modules:
        assert '--add-drivers' in run_mocked.args
        arg = run_mocked.args[run_mocked.args.index('--add-drivers') + 1]
        for m in kernel_modules:
            assert m[0] in arg
    else:
        assert '--add-drivers' not in run_mocked.args
