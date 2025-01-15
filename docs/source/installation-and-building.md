# Installation and building

We expect this software to be installed on systems always as RPM packages.
To make the development & testing easier we provide the Makefile with useful
commands for local building and also upstream DNF COPR repository for public
upstream and testing builds.

## Local builds
To build the package locally from the current code we prepared building in
containers, so we could build the RPM with packages of the particular system.
To build the RPM e.g. for RHEL 8 systems, execute:
```bash
$ BUILD_CONTAINER=el8 make container_build
```

You will find created builds under the `packaging/RPMS/` directory.

If a particular container image does not exist, it will be automatically created
based on prepared [container files](https://github.com/oamg/leapp-repository/tree/main/utils/container-builds).

Note that from time to time it's possible you may want to (or need to)
rebuild the container image. To clean created container images, call
```
$ make clean_containers
```

### Use Docker instead of Podman
If you want to use Docker instead of Podman, just specify `CONTAINER_TOOL=docker`.
E.g.:
```bash
$ CONTAINER_TOOL=docker BUILD_CONTAINER=el8 make container_build
```

### Install local builds
For that, just use DNF:
```bash
$ dnf install -y path/to/create/rpm/files
```

E.g.:
```
$ dnf install -y \
    packaging/RPMS/noarch/leapp-upgrade-el8toel9-0.21.0-0.202411131807Z.05f15b28.actor_config.el8.noarch.rpm \
    packaging/RPMS/noarch/leapp-upgrade-el8toel9-deps-0.21.0-0.202411131807Z.05f15b28.actor_config.el8.noarch.rpm
```

Note that to install packages from the leapp-repository build you also the leapp
packages installed or available. If you do not have a local builds of leapp
created manually, you can use the upstream [@oamg/leapp](https://copr.fedorainfracloud.org/coprs/g/oamg/leapp/)
COPR repository.

## Public COPR repository
The [@oamg/leapp](https://copr.fedorainfracloud.org/coprs/g/oamg/leapp/) COPR
repository contains builds for the leapp and leapp-repository projects.

Builds in the repository are created automatically by Packit when
* a PR is opened/updated
  * building for first time contributors needs to be approved by members of the upstream
  * build is made from the PR branch
  * note that the RPM release for PR builds starts with `0.` and contains
    substring `.prX.`, where the X is the PR number
* the `main` branch is updated / a PR is merged
  * build is made from the `main` branch and it's considered to be the
    upstream build
  * the rpm release starts with `100.`

Note that builds in COPR are automatically removed after 2-3 weeks but the build
with the highest [NEVRA](https://metacpan.org/pod/RPM::NEVRA)
which is considered to be the most up-to-date upstream build.
All PR builds has automatically lower NEVRA than any upstream build, so they
are always cleaned when they are considered expired by COPR.

The upstream members can trigger building in COPR manually for a PR by comment
```
/packit copr-build
```

Note that this repository is supposed to be used only for the development and
testing purposes.

### Installing builds from the COPR repository
To add the upstream [@oamg/leapp](https://copr.fedorainfracloud.org/coprs/g/oamg/leapp/)
COPR repository to your system, execute:
```bash
# dnf copr enable "@oamg/leapp"
```

Or just install one of EPEL X files you can find on the COPR repo page - see the
`Repo Download` column. (Fedora builds are only for the leapp project).

To install latest upstream build, just run:
```bash
$ dnf install -y leapp-upgrade
```

To install latest build in the repo for the PR number X:
```bash
$ dnf install -y "leapp-upgrade-*.prX.*"
```

In similar way you can install particular `leapp` packages if you want any
specific build.

#### Instructions for for non-intel architectures
All packages are `noarch` (architecture agnostic). To save a time and resources
we build packages just for the x86\_64 repository.
So in case you use a different architecture (IBM Z, Power, ARM)
replace the `$basearch` variable in the repo file by static `x86_64`.
