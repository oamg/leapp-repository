%global repositorydir %{_datadir}/leapp-repository/repositories
%global custom_repositorydir %{_datadir}/leapp-repository/custom-repositories

Name:       leapp-repository
Version:    0.4.0
Release:    1%{?dist}
Summary:    Repositories for leapp

License:    AGPLv3+
URL:        https://leapp-to.github.io
Source0:    https://github.com/oamg/leapp-repository/archive/leapp-repository-%{version}.tar.gz
Source1:    leapp-repository-initrd.tar.gz
Source2:    leapp-repository-data.tar.gz
BuildArch:  noarch
Requires:   dnf >= 2.7.5-19
Requires:   %{name}-data = %{version}-%{release}
%if 0%{?fedora} || 0%{?rhel} > 7
Requires:   systemd-container
%endif

%description
Repositories for leapp

# leapp-repository-data subpackage
%package data
License: Red Hat Enterprise Agreement
Summary: Package evolution data for leapp
Requires: %{name} = %{version}-%{release}

%description data
Package evolution data for leapp.


%prep
%autosetup -n %{name}-%{version}
%setup -q  -n %{name}-%{version} -D -T -a 1
%setup -q  -n %{name}-%{version} -D -T -a 2


%build
# ??? what is supposed to be this? we do not have any build target in the makefile
make build
cp -a leapp-repository-initrd*/vmlinuz-upgrade.x86_64       repos/system_upgrade/el7toel8/files/
cp -a leapp-repository-initrd*/initramfs-upgrade.x86_64.img repos/system_upgrade/el7toel8/files/
cp -a leapp-pes-data*/packaging/sources/pes-events.json     repos/system_upgrade/el7toel8/actors/peseventsscanner/files/


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

for DIRECTORY in $(find  %{buildroot}%{repositorydir}/  -mindepth 1 -maxdepth 1 -type d);
do
    REPOSITORY=$(basename $DIRECTORY)
    echo "Enabling repository $REPOSITORY"
    ln -s  %{repositorydir}/$REPOSITORY  %{buildroot}%{_sysconfdir}/leapp/repos.d/$REPOSITORY
done;


%files
%doc README.md
%license LICENSE
%{_sysconfdir}/leapp/repos.d/*
%{_sysconfdir}/leapp/transaction/*
%{repositorydir}/*
%dir %{custom_repositorydir}
%exclude %{repositorydir}/system_upgrade/el7toel8/actors/peseventsscanner/files/pes-events.json

%files data
%{repositorydir}/system_upgrade/el7toel8/actors/peseventsscanner/files/pes-events.json


%changelog
* Mon Apr 16 2018 Vinzenz Feenstra <evilissimo@redhat.com> - %{version}-%{release}
- Initial RPM
