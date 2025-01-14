from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.config import get_env, version
from leapp.libraries.stdlib import api
from leapp.models import IPUPaths
from leapp.utils.deprecation import suppress_deprecation

FMT_LIST_SEPARATOR = '\n    - '


@suppress_deprecation(IPUPaths)
def get_supported_target_versions():
    ipu_paths = next(api.consume(IPUPaths), None)
    src_version = version.get_source_version()
    if not ipu_paths:
        # NOTE: missing unit-tests. Unexpected situation and the solution
        # is possibly temporary
        raise StopActorExecutionError('Missing the IPUPaths message. Cannot determine defined upgrade paths.')
    for ipu_path in ipu_paths.data:
        if ipu_path.source_version == src_version:
            return ipu_path.target_versions

    # Nothing discovered. Current src_version is not already supported or not yet.
    # Problem of supported source versions is handled now separately in other
    # actors. Fallbak from X.Y versioning to major version only.
    api.current_logger().warning(
        'Cannot discover support upgrade path for this system release: {}'
        .format(src_version)
    )
    maj_version = version.get_source_major_version()
    for ipu_path in ipu_paths.data:
        if ipu_path.source_version == maj_version:
            return ipu_path.target_versions

    # Completely unknown
    api.current_logger().warning(
        'Cannot discover supported upgrade path for this system major version: {}'
        .format(maj_version)
    )
    return []


def process():
    target_version = version.get_target_version()
    supported_target_versions = get_supported_target_versions()

    if target_version in supported_target_versions:
        api.current_logger().info('Target version is supported. Continue.')
        return

    if get_env('LEAPP_UNSUPPORTED', '0') == '1':
        api.current_logger().warning(
            'Upgrading to an unsupported version of the target system but LEAPP_UNSUPPORTED=1. Continue.'
        )
        return

    # inhibit the upgrade - unsupported target and leapp running in production mode
    hint = (
            'Choose a supported version of the target OS for the upgrade.'
            ' Alternatively, if you require to upgrade using an unsupported upgrade path,'
            ' set the `LEAPP_UNSUPPORTED=1` environment variable to confirm you'
            ' want to upgrade on your own risk.'
    )

    reporting.create_report([
        reporting.Title('Specified version of the target system is not supported'),
        reporting.Summary(
            'The in-place upgrade to the specified version ({tgt_ver}) of the target system'
            ' is not supported from the current system version. Follow the official'
            ' documentation for up to date information about supported upgrade'
            ' paths and future plans (see the attached link).'
            ' The in-place upgrade is enabled to the following versions of the target system:{sep}{ver_list}'
            .format(
                sep=FMT_LIST_SEPARATOR,
                ver_list=FMT_LIST_SEPARATOR.join(supported_target_versions),
                tgt_ver=target_version
            )
        ),
        reporting.Groups([reporting.Groups.INHIBITOR]),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Remediation(hint=hint),
        reporting.ExternalLink(
            url='https://access.redhat.com/articles/4263361',
            title='Supported in-place upgrade paths for Red Hat Enterprise Linux'
        )
    ])
