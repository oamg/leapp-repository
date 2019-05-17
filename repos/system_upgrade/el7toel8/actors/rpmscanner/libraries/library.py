
def get_package_repository_data(self):
    """ Return dictionary mapping package name with repository from which it was installed """
    # import has to be inside the function to obey troubles with non-existing
    # module in Python3 (where we do not need this function anymore)
    import yum
    yum_base = yum.YumBase()
    pkg_repos = {}
    for pkg in yum_base.doPackageLists().installed:
        pkg_repos[pkg.name] = pkg.ui_from_repo.lstrip('@')

    return pkg_repos
