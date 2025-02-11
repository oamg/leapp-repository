# Dealing with dependencies
Packaging of leapp and leapp-repository is complex. In this document we explain and describe how it's done.

First, it's strongly recommended to read {external:doc}`the framework document about
dependencies<dependencies>` to understand the difficulties and decisions behind the packaging and dependencies in leapp-repository.

% When talking about a RHEL upgrade, the goal is to cover dependencies of all
% Leapp framework related packages, including the leapp-repository
% packages, for both, the source and target RHEL systems. Since the situation
% with dependencies of the leapp packages is similar to the situation with the
% leapp-repository dependencies, this document focuses on the leapp-repository
% specifics only.

## Packaging and dependencies in leapp-repository
% TODO this section might go elsewhere
As described in the document linked above, the Leapp framework is packaged as 4 separate RPMs:
- `leapp` - the leapp binary
- `pythonX-leapp` - the leapp library
- `leapp-deps` - meta-package for "outer" dependencies of leapp
- `snactor` - the snactor tool

Similarly, leapp-repository is packaged as 2 originally installable packages built using the [leapp-repository.spec](https://github.com/oamg/leapp-repository/blob/main/packaging/leapp-repository.spec) specfile:
- `leapp-upgrade-elXtoelY` - contains all of the actual content for the upgrade from RHEL X to RHEL Y
- `leapp-upgrade-elXtoelY-deps` - meta-package for dependencies of `leapp-upgrade-elXtoelY` for the source system RHEL X

```{note}
We use RHEL X and RHEL Y to refer to the major RHEL version of source and target system respectively.
```

During an in-place upgrade, the packages on the source system get upgraded,
replaced, removed, etc. This means that the dependencies required by
`leapp-deps` and `leapp-upgrade-elXtoelY-deps` might no longer be present on
the target system. For this reason these two packages built using the
[leapp-el7toel8-deps.spec](https://github.com/oamg/leapp-repository/blob/main/packaging/other_specs/leapp-el7toel8-deps.spec)
specfile (contrary to the name, it's used to build packages for all versions),
are replaced during the upgrade:
- `leapp-deps-elY` replaces `leapp-deps`
- `leapp-repository-deps-elY` replaces `leapp-upgrade-elXtoelY-deps`

These two meta-packages specify dependencies of leapp and leapp-repository for the target system RHEL Y.

### Deps packages replacement
The deps packages for the target system (`leapp-deps-elY` and `leapp-repository-deps-elY`) are bundled in the `leapp-upgrade-elXtoelY` RPM and placed in the respective leapp repository at `system_upgrade/elXtoelY/files/bundled-rpms/` at install time.

The replacement takes places during the RPM upgrade transaction done by the rhel-upgrade DNF plugin in the {ref}`upgrade-architecture-and-workflow/phases-overview:rpmupgradephase`, just like the upgrade of other packages.
The packages are passed to the plugin by a message produced by the `transactionworkarounds` actor.

## What to do in leapp-repository when dependencies of leapp change?
Go to the section below the line `%package -n %{ldname}` in the
[leapp-el7toel8-deps.spec](https://github.com/oamg/leapp-repository/blob/main/packaging/other_specs/leapp-el7toel8-deps.spec).
This section creates the RHEL Y `leapp-deps-elY` meta-package that replaces the
RHEL X `leapp-deps` meta-package.

When the leapp package dependencies change in
[leapp.spec](https://github.com/oamg/leapp/blob/main/packaging/leapp.spec),
together with incrementing version of the `leapp-framework-dependencies`
capability it's necessary to:

- provide the same `leapp-framework-dependencies` capability version by
  `leapp-deps-elY`

- decide if this dependency change also applies to RHEL Y and if so, update the
  dependencies of the `leapp-deps-elY` meta-package accordingly.

There can be another case when we need to modify dependencies of leapp on
RHEL Y, e.g. when a RHEL X package is renamed or split on RHEL Y. In such case
we don't need to modify the capability value, just update dependencies of the
`leapp-deps-elY` meta-package, commenting it properly. Nothing else.

## What to do when leapp-repository dependencies need to change?
When you want to modify *outer dependencies* of leapp-repository packages, do
that similarly to how it's done in Leapp packages, following the same
rules.

Just take care of the `leapp-repository-dependencies` capability
instead of the `leapp-framework-dependencies` capability. Everything else is
the same.
Interesting parts of the SPEC files are highlighted in the same way as
described in the {external:doc}`the framework document about
dependencies<dependencies>`.

```{seealso}
You can take a look at this commit as an example: [Update dependencies: require xfsprogs and e2fsprogs](https://github.com/oamg/leapp-repository/commit/7a819fb293340b2ed22b6d5e2816dd9c39fefdc9).
```
