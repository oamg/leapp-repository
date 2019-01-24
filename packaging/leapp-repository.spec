%global leapp_datadir %{_datadir}/leapp-repository
%global repositorydir %{leapp_datadir}/repositories
%global custom_repositorydir %{leapp_datadir}/custom-repositories

Name:       leapp-repository
Version:    0.5.0
Release:    1%{?dist}
Summary:    Repositories for leapp

License:    AGPLv3+
URL:        https://leapp-to.github.io
Source0:    https://github.com/oamg/leapp-repository/archive/leapp-repository-%{version}.tar.gz
Source1:    leapp-repository-initrd.tar.gz
Source2:    leapp-repository-data.tar.gz
Source3:    deps-pkgs.tar.gz
BuildArch:  noarch
Requires:   %{name}-data = %{version}-%{release}

# IMPORTANT: everytime the requirements are changed, increment number by one
# - same for Provides in deps subpackage
Requires:   leapp-repository-dependencies = 1

%description
Repositories for leapp

# leapp-repository-data subpackage
%package data
License: Red Hat Enterprise Agreement
Summary: Package evolution data for leapp
Requires:   %{name} = %{version}-%{release}

%description data
Package evolution data for leapp.

# This metapackage should contain all RPM dependencies exluding deps on *leapp*
# RPMs. This metapackage will be automatically replaced during the upgrade
# to satisfy dependencies with RPMs from target system.
%package deps
Summary:    Meta-package with system dependencies of %{name} package

# IMPORTANT: everytime the requirements are changed, increment number by one
# - same for Requires in main package
Provides:  leapp-repository-dependencies = 1
##################################################
# Real requirements for the leapp-repository HERE
##################################################
Requires:   dnf >= 4
%if 0%{?rhel} && 0%{?rhel} == 7
# Required to gather system facts about SELinux
Requires:   libselinux-python
%else ## RHEL 8 dependencies ##
# Requires:   systemd-container
%endif
##################################################
# end requirement
##################################################
%description deps
%{summary}

%prep
%autosetup -n %{name}-%{version}
%setup -q  -n %{name}-%{version} -D -T -a 1
%setup -q  -n %{name}-%{version} -D -T -a 2
%setup -q  -n %{name}-%{version} -D -T -a 3


%build
# ??? what is supposed to be this? we do not have any build target in the makefile
make build
cp -a leapp-repository-initrd*/vmlinuz-upgrade.x86_64       repos/system_upgrade/el7toel8/files/
cp -a leapp-repository-initrd*/initramfs-upgrade.x86_64.img repos/system_upgrade/el7toel8/files/
cp -a leapp-pes-data*/packaging/sources/pes-events.json     repos/system_upgrade/el7toel8/actors/peseventsscanner/files/
cp -a leapp*deps*rpm repos/system_upgrade/el7toel8/files/bundled-rpms/


%install
install -m 0755 -d %{buildroot}%{custom_repositorydir}
install -m 0755 -d %{buildroot}%{repositorydir}
cp -r repos/* %{buildroot}%{repositorydir}/
install -m 0755 -d %{buildroot}%{_sysconfdir}/leapp/repos.d/
install -m 0755 -d %{buildroot}%{_sysconfdir}/leapp/transaction/
install -m 0644 etc/leapp/transaction/* %{buildroot}%{_sysconfdir}/leapp/transaction

# Remove irrelevant repositories - We don't want to ship them
rm -rf %{buildroot}%{repositorydir}/containerization
rm -rf %{buildroot}%{repositorydir}/test

# remove component/unit tests, Makefiles, ... stuff that related to testing only
rm -rf %{buildroot}%{repositorydir}/common/actors/testactor
find %{buildroot}%{repositorydir}/common -name "test.py" -delete
rm -rf `find %{buildroot}%{repositorydir} -name "tests" -type d`
find %{buildroot}%{repositorydir} -name "Makefile" -delete

for DIRECTORY in $(find  %{buildroot}%{repositorydir}/  -mindepth 1 -maxdepth 1 -type d);
do
    REPOSITORY=$(basename $DIRECTORY)
    echo "Enabling repository $REPOSITORY"
    ln -s  %{repositorydir}/$REPOSITORY  %{buildroot}%{_sysconfdir}/leapp/repos.d/$REPOSITORY
done;


%files
%doc README.md
%license LICENSE
%dir %{_sysconfdir}/leapp/transaction
%dir %{leapp_datadir}
%dir %{repositorydir}
%dir %{custom_repositorydir}
%{_sysconfdir}/leapp/repos.d/*
%{_sysconfdir}/leapp/transaction/*
%{repositorydir}/*
%exclude %{repositorydir}/system_upgrade/el7toel8/actors/peseventsscanner/files/pes-events.json

%files data
%{repositorydir}/system_upgrade/el7toel8/actors/peseventsscanner/files/pes-events.json

%files deps
# no files here

%changelog
* Fri Jan 11 2019 Michal Reznik <mreznik@redhat.com> - %{version}-%{release}
- Bump dnf requires version

* Mon Apr 16 2018 Vinzenz Feenstra <evilissimo@redhat.com> - %{version}-%{release}
- Initial RPM
