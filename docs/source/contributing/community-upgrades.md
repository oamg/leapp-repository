# Community upgrades for Centos-like distros

In the past, this project was solely focused on Red Hat Enterprise Linux upgrades. Recently, we've been extending and refactoring the `leapp-repository` codebase to allow upgrades of other distributions, such as CentOS Stream and also upgrades + conversions between different distributions in one step.

This document outlines the state of support for upgrades of distributions other than RHEL. Note that support in this case doesn't mean what the codebase allows, but what the core leapp team supports in terms of issues, bugfixes, feature requests, testing, etc.

RHEL upgrades and upgrades + conversions *to* RHEL are the only officially supported upgrade paths and are the primary focus of leapp developers. However, we are open to and welcome contributions from the community, allowing other upgrade (and conversion) paths in the codebase. For example, we've already integrated a contribution introducing upgrade paths for Alma Linux upgrades.

This does not mean that we won't offer help outside of the outlined scope, but it is primarily up to the contributors contributing a particular upgrade path to maintain and test it. Also, it can take us some time to get to such PRs, so be patient please.

Upon agreement we can also update the upgrade paths (in `upgrade_paths.json`) when there is a new release of the particular distribution. However note that we might include some upgrade paths required for conversions *to* RHEL on top of that.

Contributions improving the overall upgrade experience are also welcome, as they always have been.

```{note}
By default, upgrade + conversion paths are automatically derived from upgrade paths. If this is not desired or other paths are required, feel free to open a pull request or open a [discussion](https://github.com/oamg/leapp-repository/discussions) on that topic.
```

## How to contribute

Currently, the process for enabling upgrades and conversions for other distributions is not fully documented. In the meantime you can use the [pull request introducing Alma Linux upgrades](https://github.com/oamg/leapp-repository/pull/1391/) as reference. However, note that the leapp upgrade data files have special rules for updates, described below.

### Leapp data files

#### repomap.json

To use correct target repositories during the upgrade automatically, the `repomap.json` data file needs to be updated to cover repositories of the newly added distribution. However, the file cannot be updated manually as its content is generated, hence any manual changes would be overwritten with the next update. Currently there is not straightforward way for the community to update our generators, but you can

- submit a separate PR of how the resulting `repomap.json` file should look like, for an example you can take a look at [this PR](https://github.com/oamg/leapp-repository/pull/1395)
- or provide the list of repositories (possibly also architectures) present on the distribution

and we will update the generators accordingly, asking you to review the result then. We are discussing an improvement to make this more community friendly.

#### pes-events.json and device_driver_deprecation_data.json

Both PES events and device driver deprecation data only contain data for RHEL in the upstream `leapp-repository` and we will not include any data unrelated to RHEL. If you find a bug in the data, you can open a bug in the [RHEL Jira](https://issues.redhat.com/) for the `leapp-repository` component.

Before contributing, make sure your PR conforms to our {doc}`Coding guidelines<coding-guidelines>`
 and {doc}`PR guidelines<pr-guidelines>`.
