#
#
# !!! POC !!!
#
# Lot of hardcoded stuff. No fancy macros etc.
#

Name:           leapp-rhui-aws
Version:        0.1.0
Release:        1%{?dist}
Summary:        Leapp in-place upgrade on AWS

License:        LGPLv2+
URL:            https://github.com/oamg/leapp-repository
Source0:        leapp-rhui-aws-%{version}.tar.gz

BuildArch:      noarch

Requires:       leapp leapp-repository

%description
Leapp in-place upgrade on AWS

%prep
%setup -q -n leapp-rhui-aws-%{version}

%build
# Nothing to build

%install
mkdir -p %{buildroot}/etc/leapp/files/
mkdir -p %{buildroot}/usr/lib/python2.7/site-packages/dnf-plugins/
mkdir -p %{buildroot}/usr/share/leapp-repository/repositories/system_upgrade/el7toel8/files/rhui-certs

cp leapp_upgrade_repositories.repo  %{buildroot}/etc/leapp/files/
cp content-rhel8.key %{buildroot}/usr/share/leapp-repository/repositories/system_upgrade/el7toel8/files/rhui-certs
cp rhui-client-config-server-8.key %{buildroot}/usr/share/leapp-repository/repositories/system_upgrade/el7toel8/files/rhui-certs
cp content-rhel8.crt %{buildroot}/usr/share/leapp-repository/repositories/system_upgrade/el7toel8/files/rhui-certs
cp rhui-client-config-server-8.crt %{buildroot}/usr/share/leapp-repository/repositories/system_upgrade/el7toel8/files/rhui-certs
cp cdn.redhat.com-chain.crt %{buildroot}/usr/share/leapp-repository/repositories/system_upgrade/el7toel8/files/rhui-certs
cp amazon-id.py %{buildroot}/usr/share/leapp-repository/repositories/system_upgrade/el7toel8/files

exit 0

%files
/etc/leapp/files/
/usr/share/leapp-repository/repositories/system_upgrade/el7toel8/files/rhui-certs/rhui-client-config-server-8.key
/usr/share/leapp-repository/repositories/system_upgrade/el7toel8/files/rhui-certs/content-rhel8.key
/usr/share/leapp-repository/repositories/system_upgrade/el7toel8/files/rhui-certs/rhui-client-config-server-8.crt
/usr/share/leapp-repository/repositories/system_upgrade/el7toel8/files/rhui-certs/content-rhel8.crt
/usr/share/leapp-repository/repositories/system_upgrade/el7toel8/files/rhui-certs/cdn.redhat.com-chain.crt
/usr/share/leapp-repository/repositories/system_upgrade/el7toel8/files/amazon-id.py

%changelog
