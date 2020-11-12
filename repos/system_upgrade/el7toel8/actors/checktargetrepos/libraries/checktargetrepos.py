from leapp.models import CustomTargetRepositoryFile, TargetRepositories, RHUIInfo
from leapp.libraries.stdlib import api
from leapp import reporting
from leapp.libraries.common import config, rhsm


_IPU_DOC_URL = ('https://access.redhat.com/documentation/en-us/'
                'red_hat_enterprise_linux/8/html-single/upgrading_to_rhel_8/index')
# TODO: we need to provide this path in a shared library
CUSTOM_REPO_PATH = '/etc/leapp/files/leapp_upgrade_repositories.repo'


def _any_custom_repo_defined():
    for tr in api.consume(TargetRepositories):
        if tr.custom_repos:
            return True
    return False


def _the_custom_repofile_defined():
    for ctrf in api.consume(CustomTargetRepositoryFile):
        if ctrf and ctrf.file == CUSTOM_REPO_PATH:
            return True
    return False


def _the_enablerepo_option_used():
    return config.get_env('LEAPP_ENABLE_REPOS', None) is not None


def process():

    rhui_info = next(api.consume(RHUIInfo), None)

    if not rhsm.skip_rhsm() or rhui_info:
        # getting RH repositories through RHSM or RHUI; resolved by seatbelts
        # implemented in other actors
        return

    # rhsm skipped; take your seatbelts please
    is_ctr = _any_custom_repo_defined()
    is_ctrf = _the_custom_repofile_defined()
    is_re = _the_enablerepo_option_used()
    if not is_ctr:
        # no rhsm, no custom repositories.. this will really not work :)
        # TODO: add link to the RH article about use of custom repositories!!
        # NOTE: we can put here now the link to the main document, as this
        # will be described there or at least the link to the right document
        # will be delivered here.
        if is_ctrf:
            summary_ctrf = '\n\nThe custom repository file has been detected. Maybe it is empty?'
        else:
            summary_ctrf = ''
        reporting.create_report([
            reporting.Title('Using RHSM has been skipped but no custom or RHUI repositories have been delivered.'),
            reporting.Summary(
                'Leapp is run in the mode when the Red Hat Subscription Manager'
                ' is not used (the --no-rhsm option or the LEAPP_NO_RHSM=1'
                ' environment variable has been set) so leapp is not able to'
                ' obtain YUM/DNF repositories with the content for the target'
                ' system in the standard way. The content has to be delivered'
                ' either by user manually or, in case of public clouds, by a'
                ' special Leapp package for RHUI environments.'
                ),
            reporting.Remediation(hint=(
                'Create the repository file according to instructions in the'
                ' referred document on the following path with all'
                ' repositories that should be used during the upgrade: "{}".'
                '\n\n{}'
                .format(CUSTOM_REPO_PATH, summary_ctrf)
            )),
            reporting.Severity(reporting.Severity.HIGH),
            reporting.Groups([reporting.Groups.SANITY, reporting.Groups.INHIBITOR]),
            reporting.ExternalLink(url=_IPU_DOC_URL, title='UPGRADING TO RHEL 8'),
            reporting.RelatedResource('file', CUSTOM_REPO_PATH),
        ])
    elif not (is_ctrf or is_re):
        # Some custom repositories have been discovered, but the custom repo
        # file not - neither the --enablerepo option is used. Inform about
        # the official recommended way.
        reporting.create_report([
            reporting.Title('Detected "CustomTargetRepositories" without using new provided mechanisms used.'),
            reporting.Summary(
                'Red Hat now provides an official way for using custom'
                ' repositories during the in-place upgrade through'
                ' the referred custom repository file or through the'
                ' --enablerepo option for leapp. The CustomTargetRepositories'
                ' have been produced from custom (own) actors?'
            ),
            reporting.Remediation(hint=(
                'Follow the new simple way to enable custom repositories'
                ' during the upgrade (see the referred document) or create'
                ' the empty custom repository file to acknowledge this report'
                ' message.'
            )),
            reporting.Severity(reporting.Severity.INFO),
            reporting.ExternalLink(url=_IPU_DOC_URL, title='UPGRADING TO RHEL 8'),
            reporting.RelatedResource('file', CUSTOM_REPO_PATH),
        ])
