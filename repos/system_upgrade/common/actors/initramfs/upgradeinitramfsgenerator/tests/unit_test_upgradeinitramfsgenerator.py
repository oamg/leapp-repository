import os
import shutil

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import upgradeinitramfsgenerator
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked, produce_mocked
from leapp.utils.deprecation import suppress_deprecation

from leapp.models import (  # isort:skip
    FIPSInfo,
    RequiredUpgradeInitramPackages,  # deprecated
    UpgradeDracutModule,  # deprecated
    BootContent,
    CopyFile,
    DracutModule,
    KernelModule,
    TargetUserSpaceUpgradeTasks,
    UpgradeInitramfsTasks,
)

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
PKGS = ['pkg{}'.format(c) for c in 'ABCDEFGHIJ']
FILES = [
    CopyFile(src='/host/srcfile{}'.format(i), dst='/cont/dstfile{}'.format(i))
    for i in range(5)
]
MODULES = [
    ('moduleA', None),
    ('moduleB', None),
    ('moduleC', '/some/path/moduleC'),
    ('moduleD', '/some/path/moduleD'),
]


@pytest.fixture
def adjust_cwd():
    previous_cwd = os.getcwd()
    os.chdir(os.path.join(CUR_DIR, "../"))
    yield
    os.chdir(previous_cwd)


def _ensure_list(data):
    return data if isinstance(data, list) else [data]


def gen_TUSU(packages, copy_files=None):
    packages = _ensure_list(packages)

    if not copy_files:
        copy_files = []
    copy_files = _ensure_list(copy_files)

    return TargetUserSpaceUpgradeTasks(install_rpms=packages, copy_files=copy_files)


@suppress_deprecation(RequiredUpgradeInitramPackages)
def gen_RUIP(packages):
    packages = _ensure_list(packages)
    return RequiredUpgradeInitramPackages(packages=packages)


def gen_UIT(dracut_modules, kernel_modules, files):
    files = _ensure_list(files)

    dracut_modules = [DracutModule(name=i[0], module_path=i[1]) for i in _ensure_list(dracut_modules)]
    kernel_modules = [KernelModule(name=i[0], module_path=i[1]) for i in _ensure_list(kernel_modules)]

    return UpgradeInitramfsTasks(include_files=files,
                                 include_dracut_modules=dracut_modules,
                                 include_kernel_modules=kernel_modules,
                                 )


@suppress_deprecation(UpgradeDracutModule)
def gen_UDM_list(data):
    if not isinstance(data, list):
        data = [data]
    return [UpgradeDracutModule(name=i[0], module_path=i[1]) for i in data]


class MockedContext(object):
    def __init__(self):
        self.called_copy_from = []
        self.called_copytree_from = []
        self.called_copy_to = []
        self.called_call = []
        self.called_makedirs = []
        self.content = set()
        self.base_dir = "/base/dir"
        """
        Content (paths) that should exists regarding the used methods.

        It's not 100% same. Just dst paths are copied here. Ignoring differences
        between copy to /path/to/filename and /path/to/dirname which in real
        world could be different. For our purposes it's ok as it is now.

        Point is, that in case of use context.remove_tree(), we are able to
        detect whether something what is expected to be present is not missing.
        """

    def copy_from(self, src, dst):
        self.called_copy_from.append((src, dst))

    def copytree_from(self, src, dst):
        self.called_copytree_from.append((src, dst))

    def copy_to(self, src, dst):
        self.called_copy_to.append((src, dst))
        self.content.add(dst)

    def copytree_to(self, src, dst):
        self.called_copy_to.append((src, dst))
        self.content.add(dst)

    def makedirs(self, path):
        self.called_makedirs.append(path)

    def remove_tree(self, path):
        # make list for iteration as change of the set is expected during the
        # iteration, which could lead to runtime error
        for item in list(self.content):
            # ensure the / is the last character to simulate dirname
            dir_fmt_path = path if path[-1] == '/' else path + '/'
            if item == path or item.startswith(dir_fmt_path):
                # remove the file or everything inside dir (including dir)
                self.content.remove(item)

    def call(self, *args, **kwargs):
        self.called_call.append((args, kwargs))

    def full_path(self, path):
        return os.path.join(self.base_dir, os.path.abspath(path).lstrip('/'))


class MockedLogger(logger_mocked):

    def error(self, *args, **dummy):
        self.errmsg.extend(args)


@pytest.mark.parametrize('arch', architecture.ARCH_SUPPORTED)
def test_copy_boot_files(monkeypatch, arch):
    kernel = 'vmlinuz-upgrade.{}'.format(arch)
    kernel_hmac = '.vmlinuz-upgrade.{}.hmac'.format(arch)
    initram = 'initramfs-upgrade.{}.img'.format(arch)
    bootc = BootContent(
        kernel_path=os.path.join('/boot', kernel),
        kernel_hmac_path=os.path.join('/boot', kernel_hmac),
        initram_path=os.path.join('/boot', initram)
    )

    context = MockedContext()
    monkeypatch.setattr(upgradeinitramfsgenerator.api, 'current_actor', CurrentActorMocked(arch=arch))
    monkeypatch.setattr(upgradeinitramfsgenerator.api, 'produce', produce_mocked())

    def create_upgrade_hmac_from_target_hmac_mock(original_hmac_path, upgrade_hmac_path, upgrade_kernel):
        hmac_file = '.{}.hmac'.format(upgrade_kernel)
        assert original_hmac_path == os.path.join(context.full_path('/artifacts'), hmac_file)
        assert upgrade_hmac_path == bootc.kernel_hmac_path

    monkeypatch.setattr(upgradeinitramfsgenerator,
                        'create_upgrade_hmac_from_target_hmac',
                        create_upgrade_hmac_from_target_hmac_mock)

    upgradeinitramfsgenerator.copy_boot_files(context)
    assert len(context.called_copy_from) == 2
    assert (os.path.join('/artifacts', kernel), bootc.kernel_path) in context.called_copy_from
    assert (os.path.join('/artifacts', initram), bootc.initram_path) in context.called_copy_from

    assert upgradeinitramfsgenerator.api.produce.called == 1
    assert upgradeinitramfsgenerator.api.produce.model_instances[0] == bootc


class MockedCopyArgs(object):
    def __init__(self):
        self.args = None

    def __call__(self, *args):
        self.args = args


def _sort_files(copy_files):
    return sorted(copy_files, key=lambda x: (x.src, x.dst))


def test_prepare_userspace_for_initram_no_script(monkeypatch):
    monkeypatch.setattr(upgradeinitramfsgenerator.api, 'get_actor_file_path', lambda dummy: None)
    with pytest.raises(StopActorExecutionError) as err:
        upgradeinitramfsgenerator.prepare_userspace_for_initram(MockedContext())
    assert err.value.message == 'Mandatory script to generate initram not available.'


@pytest.mark.parametrize('input_msgs,pkgs,files', [
    # deprecated packages only, without files -- original functionality
    ([gen_RUIP([])], [], []),
    ([gen_RUIP(PKGS[0])], PKGS[0], []),
    ([gen_RUIP(PKGS)], PKGS, []),

    # packages only, without files -- new analogy to previous functionality
    ([gen_TUSU([])], [], []),
    ([gen_TUSU(PKGS[0])], PKGS[0], []),
    ([gen_TUSU(PKGS)], PKGS, []),

    # packages only, mix of deprecated and new models - same sets
    ([gen_RUIP([]), gen_TUSU([])], [], []),
    ([gen_RUIP(PKGS[0]), gen_TUSU(PKGS[0])], PKGS[0], []),
    ([gen_RUIP(PKGS), gen_TUSU(PKGS)], PKGS, []),

    # packages only, mix of deprecated and new models - disjoint sets
    ([gen_RUIP(PKGS[0]), gen_TUSU(PKGS[1])], PKGS[0:2], []),
    ([gen_RUIP([]), gen_TUSU(PKGS)], PKGS, []),
    ([gen_RUIP(PKGS), gen_TUSU([])], PKGS, []),
    ([gen_RUIP(PKGS[0:5]), gen_TUSU(PKGS[5:])], PKGS, []),

    # packages only, mix of deprecated and new models - mixed
    ([gen_RUIP(PKGS[0:7]), gen_TUSU(PKGS[5:])], PKGS, []),

    # files only
    ([gen_TUSU([], FILES[0])], [], FILES[0]),
    ([gen_TUSU([], FILES)], [], FILES),

    # packages and files
    ([gen_RUIP(PKGS[0]), gen_TUSU(PKGS[1], FILES)], PKGS[0:2], FILES),
    ([gen_RUIP(PKGS[0:7]), gen_TUSU(PKGS[5:], FILES)], PKGS, FILES),
])
def test_prepare_userspace_for_initram(monkeypatch, adjust_cwd, input_msgs, pkgs, files):
    monkeypatch.setattr(upgradeinitramfsgenerator.api, 'current_actor', CurrentActorMocked(msgs=input_msgs))
    monkeypatch.setattr(upgradeinitramfsgenerator, '_install_initram_deps', MockedCopyArgs())
    monkeypatch.setattr(upgradeinitramfsgenerator, '_copy_files', MockedCopyArgs())

    context = MockedContext()
    upgradeinitramfsgenerator.prepare_userspace_for_initram(context)

    # check the upgradeinitramfsgenerator script is copied into the container
    initram_copy = (
        upgradeinitramfsgenerator.api.get_actor_file_path(upgradeinitramfsgenerator.INITRAM_GEN_SCRIPT_NAME),
        os.path.join('/', upgradeinitramfsgenerator.INITRAM_GEN_SCRIPT_NAME)
    )
    assert initram_copy in context.called_copy_to

    # check the set of packages required to be installed matches expectations
    _pkgs = set(pkgs) if isinstance(pkgs, list) else set([pkgs])
    assert upgradeinitramfsgenerator._install_initram_deps.args[0] == _pkgs

    # check the set of files to be copied into the container matches exp
    _files = _sort_files(files) if isinstance(files, list) else [files]
    assert _sort_files(upgradeinitramfsgenerator._copy_files.args[1]) == _files


class MockedGetFspace(object):
    def __init__(self, space):
        self.space = space

    def __call__(self, dummy_path, convert_to_mibs=False):
        if not convert_to_mibs:
            return self.space
        return int(self.space / 1024 / 1024)  # noqa: W1619; pylint: disable=old-division


@pytest.mark.parametrize('input_msgs,dracut_modules,kernel_modules', [
    # test dracut modules with UpgradeDracutModule(s) - orig functionality
    (gen_UDM_list(MODULES[0]), MODULES[0], []),
    (gen_UDM_list(MODULES), MODULES, []),

    # test dracut modules with UpgradeInitramfsTasks - new functionality
    ([gen_UIT(MODULES[0], MODULES[0], [])], MODULES[0], MODULES[0]),
    ([gen_UIT(MODULES, MODULES, [])], MODULES, MODULES),

    # test dracut modules with old and new models
    (gen_UDM_list(MODULES[1]) + [gen_UIT(MODULES[2], [], [])], MODULES[1:3], []),
    (gen_UDM_list(MODULES[2:]) + [gen_UIT(MODULES[0:2], [], [])], MODULES, []),
    (gen_UDM_list(MODULES[1]) + [gen_UIT([], MODULES[2], [])], MODULES[1], MODULES[2]),
    (gen_UDM_list(MODULES[2:]) + [gen_UIT([], MODULES[0:2], [])], MODULES[2:], MODULES[0:2]),

    # TODO(pstodulk): test include files missing (relates #376)
])
def test_generate_initram_disk(monkeypatch, input_msgs, dracut_modules, kernel_modules):
    context = MockedContext()
    curr_actor = CurrentActorMocked(msgs=input_msgs, arch=architecture.ARCH_X86_64)
    monkeypatch.setattr(upgradeinitramfsgenerator.api, 'current_actor', curr_actor)
    monkeypatch.setattr(upgradeinitramfsgenerator, 'copy_dracut_modules', MockedCopyArgs())
    monkeypatch.setattr(upgradeinitramfsgenerator, '_get_target_kernel_version', lambda _: '')
    monkeypatch.setattr(upgradeinitramfsgenerator, 'copy_kernel_modules', MockedCopyArgs())
    monkeypatch.setattr(upgradeinitramfsgenerator, 'copy_boot_files', lambda dummy: None)
    monkeypatch.setattr(upgradeinitramfsgenerator, '_get_fspace', MockedGetFspace(2*2**30))
    upgradeinitramfsgenerator.generate_initram_disk(context)

    # TODO(pstodulk): add tests for the check of the free space (sep. from this func)

    # test now just that all modules have been passed for copying - so we know
    # all modules have been consumed
    detected_dracut_modules = set()
    _dracut_modules = set(dracut_modules) if isinstance(dracut_modules, list) else set([dracut_modules])
    for dracut_module in upgradeinitramfsgenerator.copy_dracut_modules.args[1]:
        module = (dracut_module.name, dracut_module.module_path)
        assert module in _dracut_modules
        detected_dracut_modules.add(module)
    assert detected_dracut_modules == _dracut_modules

    detected_kernel_modules = set()
    _kernel_modules = set(kernel_modules) if isinstance(kernel_modules, list) else set([kernel_modules])
    for kernel_module in upgradeinitramfsgenerator.copy_kernel_modules.args[1]:
        module = (kernel_module.name, kernel_module.module_path)
        assert module in _kernel_modules
        detected_kernel_modules.add(module)
    assert detected_kernel_modules == _kernel_modules

    # TODO(pstodulk): this test is not created properly, as context.call check
    # is skipped completely. Testing will more convenient with fixed #376
    # similar to the files...


def test_copy_dracut_modules_rmtree_ignore(monkeypatch):
    context = MockedContext()

    def raise_env_error(dummy):
        raise EnvironmentError('an error')

    def mock_context_path_exists(path):
        full_path_content = {context.full_path(i) for i in context.content}
        return full_path_content.intersection(set([path, path + '/'])) != set()

    monkeypatch.setattr(os.path, 'exists', mock_context_path_exists)
    dmodules = [DracutModule(name='foo', module_path='/path/foo')]
    upgradeinitramfsgenerator.copy_dracut_modules(context, dmodules)
    assert context.content

    # env error should be ignored in this case
    context.content = set()
    context.remove_tree = raise_env_error
    upgradeinitramfsgenerator.copy_dracut_modules(context, dmodules)
    assert context.content


@pytest.mark.parametrize('kind', ['dracut', 'kernel'])
def test_copy_modules_fail(monkeypatch, kind):
    context = MockedContext()

    def copytree_to_error(src, dst):
        raise shutil.Error('myerror: {}, {}'.format(src, dst))

    def mock_context_path_exists(path):
        full_path_content = {context.full_path(i) for i in context.content}
        return full_path_content.intersection(set([path, path + '/'])) != set()

    context.copytree_to = copytree_to_error
    monkeypatch.setattr(os.path, 'exists', mock_context_path_exists)
    monkeypatch.setattr(upgradeinitramfsgenerator.api, 'current_logger', MockedLogger())
    monkeypatch.setattr(upgradeinitramfsgenerator, '_get_target_kernel_modules_dir', lambda _: '/kernel_modules')

    module_class = None
    copy_fn = None
    if kind == 'dracut':
        module_class = DracutModule
        copy_fn = upgradeinitramfsgenerator.copy_dracut_modules
        dst_path = 'dracut'
    elif kind == 'kernel':
        module_class = KernelModule
        copy_fn = upgradeinitramfsgenerator.copy_kernel_modules
        dst_path = 'kernel_modules'

    modules = [module_class(name='foo', module_path='/path/foo')]
    with pytest.raises(StopActorExecutionError) as err:
        copy_fn(context, modules)
    assert err.value.message.startswith('Failed to install {kind} modules'.format(kind=kind))
    expected_err_log = 'Failed to copy {kind} module "foo" from "/path/foo" to "/base/dir/{dst_path}"'.format(
            kind=kind, dst_path=dst_path)
    assert expected_err_log in upgradeinitramfsgenerator.api.current_logger.errmsg


@pytest.mark.parametrize('kind', ['dracut', 'kernel'])
def test_copy_modules_duplicate_skip(monkeypatch, kind):
    context = MockedContext()

    def mock_context_path_exists(path):
        full_path_content = {context.full_path(i) for i in context.content}
        return full_path_content.intersection(set([path, path + '/'])) != set()

    monkeypatch.setattr(os.path, 'exists', mock_context_path_exists)
    monkeypatch.setattr(upgradeinitramfsgenerator.api, 'current_logger', MockedLogger())
    monkeypatch.setattr(upgradeinitramfsgenerator, '_get_target_kernel_modules_dir', lambda _: '/kernel_modules')

    module_class = None
    copy_fn = None
    if kind == 'dracut':
        module_class = DracutModule
        copy_fn = upgradeinitramfsgenerator.copy_dracut_modules
    elif kind == 'kernel':
        module_class = KernelModule
        copy_fn = upgradeinitramfsgenerator.copy_kernel_modules

    module = module_class(name='foo', module_path='/path/foo')
    modules = [module, module]

    copy_fn(context, modules)

    debugmsg = 'The foo {kind} module has been already installed. Skipping.'.format(kind=kind)
    assert context.content
    assert len(context.called_copy_to) == 1
    assert debugmsg in upgradeinitramfsgenerator.api.current_logger.dbgmsg
