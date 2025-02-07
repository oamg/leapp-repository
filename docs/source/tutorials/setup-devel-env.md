# How to setup the development environment

To ensure you can follow the other guidelines, here we are adding tips how
to prepare your development environment.

## Clone official leapp repositories for IPU

If you are creating your custom content for IPU or want to contribute to the
upstream leapp-repository project, most likely you will want to have the
repository cloned to be able to
* get insipration from existing content
* search what you could use from the prepared content (shared libraries,
existing models, ...)
* etc.

Simply clone the [official upstream repository](https://github.com/oamg/leapp-repository) using Git:
```shell
git clone git@github.com:oamg/leapp-repository.git
```

In case you want to contribute to the upstream project, [fork the repository](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo).

## Install snactor
Simply follow instructions in the leapp tutorials [here](https://leapp.readthedocs.io/en/latest/devenv-install.html)

## Register IPU repositories in snactor

By default, repositories on your system are not registered for snactor unless
you created them on your system with snactor directly. So typically `snactor`
commands working with existing repositories does not work correctly. To register
all wanted repositories, go to the cloned leapp-repository repository and make
snactor to search all repos:
```shell
snactor repo find --path repos/
```

This will register all leapp repositories in the project. You can list all
registered repositories with snactor using: `snactor repo list`.

The configuration file with registered repositories is by default here: `~/.config/leapp/repos.json`

```{warning}
If you are on system with installed `leapp-upgrade-*` RPMs and you register
the upgrade repositories from installed packages using `snactor`, it's possible it will
not be the best idea to register also repositories from the cloned Git repository.
In such a case we suggest to use different config files when trying
to work with snactor in one or the other set of repositories. See the `--config`
option. You can also always clear the file and re-register repositories you
want again.
```
