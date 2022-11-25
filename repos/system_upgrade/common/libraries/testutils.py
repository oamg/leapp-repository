import json
import logging
import os
from collections import namedtuple

from leapp import reporting
from leapp.libraries.common.config import architecture
from leapp.models import EnvVar
from leapp.utils.deprecation import deprecated


class produce_mocked(object):
    def __init__(self):
        self.called = 0
        self.model_instances = []

    def __call__(self, *model_instances):
        self.called += len(model_instances)
        self.model_instances.extend(list(model_instances))


class create_report_mocked(object):
    def __init__(self):
        self.called = 0
        self.reports = []

    def __call__(self, report_fields):
        self.called += 1
        report_obj = reporting._create_report_object(report_fields)
        full_report = json.loads(report_obj.dump()['report'])
        self.reports.append(full_report)

    @property
    def report_fields(self):
        if self.reports:
            return self.reports[-1]
        return {}


class logger_mocked(object):
    def __init__(self):
        self.dbgmsg = []
        self.infomsg = []
        self.warnmsg = []
        self.errmsg = []

    def debug(self, *args):
        self.dbgmsg.extend(args)

    def info(self, *args):
        self.infomsg.extend(args)

    @deprecated(since='2020-09-23', message=(
        'The logging.warn method has been deprecated since Python 3.3.'
        'Use the warning method instead.'
    ))
    def warn(self, *args):
        self.warnmsg.extend(args)

    def warning(self, *args):
        self.warnmsg.extend(args)

    def error(self, *args):
        self.errmsg.extend(args)

    def __call__(self):
        return self


class CurrentActorMocked(object):  # pylint:disable=R0904
    def __init__(self, arch=architecture.ARCH_X86_64, envars=None, kernel='3.10.0-957.43.1.el7.x86_64',
                 release_id='rhel', src_ver='7.8', dst_ver='8.1', msgs=None, flavour='default'):
        envarsList = [EnvVar(name=k, value=v) for k, v in envars.items()] if envars else []
        version = namedtuple('Version', ['source', 'target'])(src_ver, dst_ver)
        release = namedtuple('OS_release', ['release_id', 'version_id'])(release_id, src_ver)

        self._common_folder = '../../files'
        self._common_tools_folder = '../../tools'
        self._actor_folder = 'files'
        self._actor_tools_folder = 'tools'
        self.configuration = namedtuple(
            'configuration', ['architecture', 'kernel', 'leapp_env_vars', 'os_release', 'version', 'flavour']
        )(arch, kernel, envarsList, release, version, flavour)
        self._msgs = msgs or []

    def __call__(self):
        return self

    def get_common_folder_path(self, folder):
        return os.path.join(self._common_folder, folder)

    def get_common_tool_path(self, name):
        return os.path.join(self._common_tools_folder, name)

    def consume(self, model):
        return iter(filter(  # pylint:disable=W0110,W1639
            lambda msg: isinstance(msg, model), self._msgs
        ))

    @property
    def log(self):
        return logging.getLogger(__name__)

    def get_actor_file_path(self, name):
        return os.path.join(self._actor_folder, name)

    # other functions and properties from the API - can be implemented as needed

    def serialize(self):
        raise NotImplementedError

    def get_answers(self, dialog):
        raise NotImplementedError

    def show_message(self, message):
        raise NotImplementedError

    @property
    def actor_files_paths(self):
        raise NotImplementedError

    @property
    def files_paths(self):
        raise NotImplementedError

    @property
    def common_files_paths(self):
        raise NotImplementedError

    @property
    def actor_tools_paths(self):
        raise NotImplementedError

    @property
    def common_tools_paths(self):
        raise NotImplementedError

    @property
    def tools_paths(self):
        raise NotImplementedError

    def get_folder_path(self, name):
        raise NotImplementedError

    def get_actor_folder_path(self, name):
        raise NotImplementedError

    def get_file_path(self, name):
        raise NotImplementedError

    def get_common_file_path(self, name):
        raise NotImplementedError

    def get_tool_path(self, name):
        raise NotImplementedError

    def get_actor_tool_path(self, name):
        raise NotImplementedError

    def run(self, *args):
        raise NotImplementedError

    def produce(self, *models):
        raise NotImplementedError

    def report_error(self, message, severity, details):
        raise NotImplementedError


def make_IOError(error):
    """
    Create an IOError instance

    Create an IOError instance with the given error number.

    :param error: the error number, e.g. errno.ENOENT
    """
    return IOError(error, os.strerror(error))


def make_OSError(error):
    """
    Create an OSError instance

    Create an OSError instance with the given error number.

    :param error: the error number, e.g. errno.ENOENT
    """
    return OSError(error, os.strerror(error))
