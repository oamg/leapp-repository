from leapp.exceptions import StopActorExecutionError


def get_package_repository_data():
    """ Return dictionary mapping package name with repository from which it was installed """
    # import has to be inside the function to avoid troubles with non-existing
    # module in Python3 (where we do not need this function anymore)
    import yum
    yum_base = yum.YumBase()
    pkg_repos = {}

    try:
        for pkg in yum_base.doPackageLists().installed:
            pkg_repos[pkg.name] = pkg.ui_from_repo.lstrip('@')
    except ValueError as e:
        if 'locale' not in str(e):  # reraise if error is not related to locales
            raise e
        raise StopActorExecutionError(
            message='Failed to get installed RPM packages because of an invalid locale',
            details={
                'hint': 'Please run leapp with a valid locale. ' +
                        'You can get a list of installed locales by running `locale -a`.'
            })

    return pkg_repos
