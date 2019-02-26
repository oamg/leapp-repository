%global  lrdname  leapp-repository-deps-el8
%global  ldname   leapp-deps-el8

Name:       leapp-el7toel8-deps
Version:    5.0.0
Release:    1%{?dist}
Summary:    Dependencies for *leapp* packages
BuildArch:  noarch

License:    AGPLv3+
URL:        https://leapp-to.github.io

%description
%{summary}

##################################################
# DEPS FOR LEAPP REPOSITORY ON RHEL 8
##################################################
%package -n %{lrdname}
Summary:    Meta-package with system dependencies for leapp repository
Provides:   leapp-repository-dependencies = 2
Obsoletes:  leapp-repository-deps

Requires:   dnf >= 4
Requires:   pciutils

%description -n %{lrdname}
%{summary}

##################################################
# DEPS FOR LEAPP FRAMEWORK ON RHEL 8
##################################################
%package -n %{ldname}
Summary:    Meta-package with system dependencies for leapp framework
Provides:   leapp-framework-dependencies = 2
Obsoletes:  leapp-deps

Requires:   python2-six
Requires:   python2-setuptools
Requires:   python2-jinja2
Requires:   findutils

%description -n %{ldname}
%{summary}

%prep

%build

%install

# do not create main packages
#%files

%files -n %{lrdname}
# no files here

%files -n %{ldname}
# no files here

%changelog
* Tue Jan 22 2019 Petr Stodulka <pstodulk@redhat.com> - %{version}-%{release}
- Initial rpm
