# How to create custom content for IPU

The official leapp repositories for in-place upgrade cover usually only RPM packages
signed by official distribution's GPG keys. Other content (third-party RPMs -
including EPEL, custom installed content, ..) needs to be covered separately.
In some cases there is not a better (or other) way than creating additional actors
to customize the IPU process.

To simplify troubleshooting for us and others (and prevent other possible problems)
we request custom actors to be installed into own leapp repositories
on the system which should be located inside the `/usr/share/leapp-repository/custom-repositories/`
directory.

This guide explains how to create custom leapp actors and repositories on the system and
how to ensure they are discovered and processed by Leapp. For the simplification
consider that custom content includes third-party content as well.

For the purpose of this guide install the `snactor` utility.

## Create custom repository

To keep it simple, instructions covers the creation of the custom leapp repository
on the system with installed `leapp` and `leapp-upgrade-*` (and `snactor`) packages.
For in-place upgrade of RHEL systems see also [official instructions](https://access.redhat.com/articles/4977891#create-custom-actor).

```{note}
If you want to create new leapp repository in your development environment without
installing `leapp-upgrade-*` packages, you will need clone the leapp-repository
git repo and register related leapp repositories using `snactor` manually. See
`snactor repo find --help` for more info.
```


1. Go to the directory where a new Leapp repository should be created:
   ```shell
   cd /usr/share/leapp-repository/custom-repositories/
   ```

2. Create a new Leapp repository:
   ```shell
   snactor repo new <repository_name>
   ```

   Read carefully [Naming Convention](#naming-convention) section to choose a right
   name to prevent possible conflicts with other content.

   ```{note}
   Note that snactor does not have to create automatically whole directory structure
   inside the repository (directories like `tools`, `libraries`, etc...). Create
   any needed directories manually. See [Repository directory layout](https://leapp.readthedocs.io/en/latest/repository-dir-layout.html) for more info.
   ```

3. Go to the newly created leapp repository:
   ```shell
   cd /usr/share/leapp-repository/custom-repositories/<repository_name>
   ```

4. [Link other needed repositories](https://leapp.readthedocs.io/en/latest/repo-linking.html)
   into the newly created custom repository. You should always link following repositories:
   ```shell
   snactor repo link --path /usr/share/leapp-repository/repositories/system_upgrade/common
   snactor repo link --path /usr/share/leapp-repository/repositories/common
   ```
   In case you need any content present in particular `.../system_upgrade/elXtoelY`
   repository, link it too.

   ```{note}
   All defined links are understood as requirements for the correct functioning
   of the custom leapp repository. E.g. adding dependency on `system_upgrade_el8toel9`
   repository means that the custom repository can bee installed and used only on
   RHEL 8 (including RHEL-like) system as the `system_upgrade_el8toel9` is present
   only there.
   ```

5. Create a symlink in `/etc/leapp/repos.d/` to register your repository for leapp:
   ```shell
   ln -s /usr/share/leapp-repository/custom-repositories/<repository_name> /etc/leapp/repos.d/
   ```

   ```{note}
   This step is required to be done just on the system where the custom repository
   is installed so leapp will discover the repository.
   ```

Note that such a created leapp repository can be installed to other systems as it is,
just the symlink needs to be always created as well (step `5`).

## Create custom actor

To create custom actors inside the newly created custom leapp repository follow
the tutorial [Writing an Actor for Leapp Upgrade](howto-first-actor-upgrade)
and read the **Naming convention** section below.


## Naming convention

The system can contain number of leapp repositories and actors. Also, the leapp framework
is focused on making lives of developers as simple as possible, but it is
paid by missing namespacing. So developers are responsible to choose wisely
names of their leapp repositories, actors, models, and libraries to ensure
they do not conflict with others. To help you to prevent possible conflicts
we propose following conventions:

1. If you create solutions for your personal use that will not be shared with
others, use e.g. the `my_custom_` prefix for the repository name. Similar can be applied
for all other leapp entities (actors, models, libraries, ...).
2. If you are SW vendor and want to create solution for your customers,
make the name of your company or product part of the leapp repository name.
3. Do not use generic names for leapp actors, models, and repositories. E.g.
creating actor that checks MySQL configuration with the `check_config` or `check_database` names
are really bad. `check_config_mysql` or `check_config_mysql_vX` is better but if multiple
products on market use the same MySQL version X and can be present on the same system,
it's still not ideal. So e.g. `check_config_mysql_<company>`
or `check_config_mysql_<product>`, where product is your unique product you deliver,
is much better option.
4. Similar applies for libraries. Creating library `databases` or `mysql` is too much
generic.

