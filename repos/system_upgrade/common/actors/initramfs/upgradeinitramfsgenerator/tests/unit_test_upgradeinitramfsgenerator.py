import os
import shutil

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import upgradeinitramfsgenerator
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked, produce_mocked
from leapp.models import (
    RequiredUpgradeInitramPackages,  # deprecated
    UpgradeDracutModule,  # deprecated
    BootContent,
    CopyFile,
    DracutModule,
    TargetUserSpaceUpgradeTasks,
    UpgradeInitramfsTasks,
)
from leapp.utils.deprecation import suppress_deprecation

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


def gen_TUSU(packages, copy_files=None):
    if not isinstance(packages, list):
        packages = [packages]
    if not copy_files:
        copy_files = []
    elif not isinstance(copy_files, list):
        copy_files = [copy_files]
    return TargetUserSpaceUpgradeTasks(install_rpms=packages, copy_files=copy_files)


@suppress_deprecation(RequiredUpgradeInitramPackages)
def gen_RUIP(packages):
    if not isinstance(packages, list):
        packages = [packages]
    return RequiredUpgradeInitramPackages(packages=packages)


def gen_UIT(modules, files):
    if not isinstance(modules, list):
        modules = [modules]
    if not isinstance(files, list):
        files = [files]
    dracut_modules = [DracutModule(name=i[0], module_path=i[1]) for i in modules]
    return UpgradeInitramfsTasks(include_files=files, include_dracut_modules=dracut_modules)


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
    initram = 'initramfs-upgrade.{}.img'.format(arch)
    bootc = BootContent(
        kernel_path=os.path.join('/boot', kernel),
        initram_path=os.path.join('/boot', initram)
    )

    monkeypatch.setattr(upgradeinitramfsgenerator.api, 'current_actor', CurrentActorMocked(arch=arch))
    monkeypatch.setattr(upgradeinitramfsgenerator.api, 'produce', produce_mocked())
    context = MockedContext()
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


@pytest.mark.parametrize('input_msgs,modules', [
    # test dracut modules with UpgradeDracutModule(s) - orig functionality
    (gen_UDM_list(MODULES[0]), MODULES[0]),
    (gen_UDM_list(MODULES), MODULES),

    # test dracut modules with UpgradeInitramfsTasks - new functionality
    ([gen_UIT(MODULES[0], [])], MODULES[0]),
    ([gen_UIT(MODULES, [])], MODULES),

    # test dracut modules with old and new models
    (gen_UDM_list(MODULES[1]) + [gen_UIT(MODULES[2], [])], MODULES[1:3]),
    (gen_UDM_list(MODULES[2:]) + [gen_UIT(MODULES[0:2], [])], MODULES),

    # TODO(pstodulk): test include files missing (relates #376)
])
def test_generate_initram_disk(monkeypatch, input_msgs, modules):
    context = MockedContext()
    curr_actor = CurrentActorMocked(msgs=input_msgs, arch=architecture.ARCH_X86_64)
    monkeypatch.setattr(upgradeinitramfsgenerator.api, 'current_actor', curr_actor)
    monkeypatch.setattr(upgradeinitramfsgenerator, 'copy_dracut_modules', MockedCopyArgs())
    monkeypatch.setattr(upgradeinitramfsgenerator, 'copy_boot_files', lambda dummy: None)
    upgradeinitramfsgenerator.generate_initram_disk(context)

    # test now just that all modules have been passed for copying - so we know
    # all modules have been consumed
    detected_modules = set()
    _modules = set(modules) if isinstance(modules, list) else set([modules])
    for dracut_module in upgradeinitramfsgenerator.copy_dracut_modules.args[1]:
        module = (dracut_module.name, dracut_module.module_path)
        assert module in _modules
        detected_modules.add(module)
    assert detected_modules == _modules

    # TODO(pstodulk): this test is not created properly, as context.call check
    # is skipped completely. Testing will more convenient with fixed #376
    # similar fo the files...


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


def test_copy_dracut_modules_fail(monkeypatch):
    context = MockedContext()

    def copytree_to_error(src, dst):
        raise shutil.Error('myerror: {}, {}'.format(src, dst))

    def mock_context_path_exists(path):
        full_path_content = {context.full_path(i) for i in context.content}
        return full_path_content.intersection(set([path, path + '/'])) != set()

    context.copytree_to = copytree_to_error
    monkeypatch.setattr(os.path, 'exists', mock_context_path_exists)
    monkeypatch.setattr(upgradeinitramfsgenerator.api, 'current_logger', MockedLogger())
    dmodules = [DracutModule(name='foo', module_path='/path/foo')]
    with pytest.raises(StopActorExecutionError) as err:
        upgradeinitramfsgenerator.copy_dracut_modules(context, dmodules)
    assert err.value.message.startswith('Failed to install dracut modules')
    expected_err_log = 'Failed to copy dracut module "foo" from "/path/foo" to "/base/dir/dracut"'
    assert expected_err_log in upgradeinitramfsgenerator.api.current_logger.errmsg


def test_copy_dracut_modules_duplicate_skip(monkeypatch):
    context = MockedContext()

    def mock_context_path_exists(path):
        full_path_content = {context.full_path(i) for i in context.content}
        return full_path_content.intersection(set([path, path + '/'])) != set()

    monkeypatch.setattr(os.path, 'exists', mock_context_path_exists)
    monkeypatch.setattr(upgradeinitramfsgenerator.api, 'current_logger', MockedLogger())
    dm = DracutModule(name='foo', module_path='/path/foo')
    dmodules = [dm, dm]
    debugmsg = 'The foo dracut module has been already installed. Skipping.'
    upgradeinitramfsgenerator.copy_dracut_modules(context, dmodules)
    assert context.content
    assert len(context.called_copy_to) == 1
    assert debugmsg in upgradeinitramfsgenerator.api.current_logger.dbgmsg
