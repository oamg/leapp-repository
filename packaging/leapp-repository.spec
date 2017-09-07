%global gittag master

%global repositorydir %{_datadir}/leapp-repository/repositories
%global custom_repositorydir %{_datadir}/leapp-repository/custom-repositories

Name:       leapp-repository
Version:    0.3.1
Release:    1%{?dist}
Summary:    Repositories for leapp

License:    AGPLv3+
URL:        https://leapp-to.github.io
Source0:    https://github.com/leapp-to/leapp-actors/archive/%{gittag}/leapp-repository-%{version}.tar.gz
BuildArch:  noarch
Requires:   dnf >= 2.7.5
%if 0%{?fedora} || 0%{?rhel} > 7
Requires:   systemd-container
%endif
%description
Repositories for leapp

%prep
%autosetup -n leapp-repository-%{gittag}


%build
make build

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


%changelog
* Mon Apr 16 2018 Vinzenz Feenstra <evilissimo@redhat.com> - %{version}-%{release}
- Initial RPM
