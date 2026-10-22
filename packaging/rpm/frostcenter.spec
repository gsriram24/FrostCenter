Name:           frostcenter
Version:        0.1.0
Release:        1%{?dist}
Summary:        MSI laptop fan control and thermal monitoring for Linux

License:        GPL-3.0-or-later
URL:            https://github.com/gsriram24/FrostCenter
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
Requires:       python3 >= 3.8
Requires:       python3-gobject
Requires:       gtk3
Requires:       polkit

%description
FrostCenter is a modern GTK3 application for monitoring and controlling
fan curves, temperature thresholds, and battery health on MSI laptops
via direct ACPI Embedded Controller (EC) port I/O (/dev/port).

%prep
%autosetup -n %{name}-%{version}

%build
# Pure python application, no compilation step needed

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_datadir}/frostcenter/models
mkdir -p %{buildroot}%{_datadir}/frostcenter/ui
mkdir -p %{buildroot}%{_datadir}/applications
mkdir -p %{buildroot}%{_datadir}/icons/hicolor/scalable/apps
mkdir -p %{buildroot}%{_datadir}/polkit-1/actions
mkdir -p %{buildroot}%{_datadir}/metainfo

install -m 755 packaging/frost %{buildroot}%{_bindir}/frost
install -m 644 OFC.py %{buildroot}%{_datadir}/frostcenter/
install -m 644 ec_access.py %{buildroot}%{_datadir}/frostcenter/
install -m 644 model_config.py %{buildroot}%{_datadir}/frostcenter/
install -m 644 version.py %{buildroot}%{_datadir}/frostcenter/
install -m 644 models/database.json %{buildroot}%{_datadir}/frostcenter/models/
install -m 644 ui/*.py %{buildroot}%{_datadir}/frostcenter/ui/

install -m 644 packaging/io.github.gsriram24.frostcenter.desktop %{buildroot}%{_datadir}/applications/
install -m 644 assets/frostcenter.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/
install -m 644 packaging/polkit/io.github.gsriram24.frostcenter.policy %{buildroot}%{_datadir}/polkit-1/actions/
install -m 644 packaging/metainfo/io.github.gsriram24.frostcenter.metainfo.xml %{buildroot}%{_datadir}/metainfo/

%postun
if [ $1 -eq 0 ]; then
    rm -rf %{_datadir}/frostcenter
fi

%files
%license LICENSE
%doc README.md CONTRIBUTING.md
%{_bindir}/frost
%{_datadir}/frostcenter/
%{_datadir}/applications/io.github.gsriram24.frostcenter.desktop
%{_datadir}/icons/hicolor/scalable/apps/frostcenter.svg
%{_datadir}/polkit-1/actions/io.github.gsriram24.frostcenter.policy
%{_datadir}/metainfo/io.github.gsriram24.frostcenter.metainfo.xml

%changelog
* Thu Oct 22 2026 G Sriram <gsriram2403@gmail.com> - 0.1.0-1
- Initial public beta release of FrostCenter
