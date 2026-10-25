# OkumarchyLaunchpad

A fast, theme-aware fullscreen application launcher for Omarchy's Quickshell desktop.

Project: https://github.com/OKUMARCHY/Launchpad

## Features

- Fullscreen application grid on the focused monitor, without reserving desktop space.
- Compact search, keyboard navigation, mouse activation, and smooth touchpad scrolling.
- Live Omarchy theme colors and the active bar's font, matching OkumarchyDock.
- Short fade/scale transitions: 90ms opening and 70ms closing by default.
- Direct icon-file indexing to avoid Qt icon-theme failures after login.
- Included fallback artwork, asynchronous icon refresh, and application diagnostics.
- Native four-finger pinch to open and three/four-finger spread to close via optional Hyprland bindings.
- Keep-loaded Omarchy panel: no additional launcher daemon or raw input permissions.

All project-authored code, interface labels, documentation, and tests are English.
Application names and metadata come from installed desktop entries and retain their original language.

## Compatibility

This is an **Omarchy plugin**, not a standalone launcher. It requires:

- Omarchy's Quickshell shell with schema-version-1 plugins, keep-loaded panels,
  the `open`/`close` lifecycle, and the shared `qs.Commons` theme.
- Hyprland and Quickshell with QtQuick Controls, Io, Wayland, Hyprland, and DesktopEntries support.
- Python 3, `uwsm-app`, and `gtk-launch` for icon discovery and application activation.
- The Hyprland Lua gesture API for optional native touchpad integration.

Compatibility is API-based; no minimum Omarchy release is claimed without broader testing.
Legacy Waybar-based Omarchy installations and other compositors are not supported.

## Installation

Once this repository is published:

```bash
omarchy plugin add https://github.com/OKUMARCHY/Launchpad.git --enable
```

For a local checkout, use a clean target:

```bash
mkdir -p ~/.config/omarchy/plugins
cp -a /path/to/OkumarchyLaunchpad ~/.config/omarchy/plugins/launchpad.okuma.dev
omarchy plugin validate ~/.config/omarchy/plugins/launchpad.okuma.dev
omarchy-shell shell rescanPlugins
omarchy plugin enable launchpad.okuma.dev
omarchy restart shell
```

Do not overwrite an existing plugin directory with `cp`. Review the source before enabling:
plugins run unsandboxed as your user. No packaged Omarchy files need modification.

```bash
omarchy-shell shell summon launchpad.okuma.dev '{}'
omarchy-shell shell hide launchpad.okuma.dev
omarchy-shell shell toggle launchpad.okuma.dev '{}'
```

**Plugin installation does not register touchpad gestures.** Enable the plugin first,
then run the opt-in setup command on each device (use your actual installation path):

```bash
python3 ~/.config/omarchy/plugins/launchpad.okuma.dev/setup-gestures.py install
```

The command backs up the existing user `input.lua`, installs a managed binding block,
reloads Hyprland, and checks configuration errors. It refuses obvious duplicate pinch
bindings; review other included files too. It does not change packaged files or global
touchpad settings. The user input.lua must already be loaded by your Hyprland config.

```bash
python3 ~/.config/omarchy/plugins/launchpad.okuma.dev/doctor.py
python3 ~/.config/omarchy/plugins/launchpad.okuma.dev/setup-gestures.py remove
```

See [docs/integration.md](docs/integration.md) before migrating from the earlier
standalone launcher. Plugin updates do not automatically rewrite gesture bindings;
rerun setup after updating. Creating this repository does not change your desktop.

## Controls

| Input | Action |
| --- | --- |
| Type | Filter application names, descriptions, and keywords |
| Enter / left click | Launch the selected application |
| Up / down | Move one grid row |
| Tab / Shift+Tab | Select the next / previous application |
| Left / right | Move selection when search is empty; edit text otherwise |
| Two-finger scroll / mouse wheel | Browse the application grid |
| Escape / outer background click | Close the launcher |
| Four-finger pinch inward | Open, with the optional gesture configuration |
| Three/four-finger spread outward | Close, with the optional gesture configuration |

## Configuration and management

Settings belong in this plugin's entry in `~/.config/omarchy/shell.json`.
Preserve all other shell settings. See [docs/configuration.md](docs/configuration.md)
and [examples/plugin-settings.json](examples/plugin-settings.json).

```bash
omarchy plugin disable launchpad.okuma.dev
omarchy plugin enable launchpad.okuma.dev
omarchy plugin update launchpad.okuma.dev
omarchy-shell shell call launchpad.okuma.dev status ''
omarchy-shell shell call launchpad.okuma.dev iconDiagnostics ''
```

Git-managed updates require installation through `omarchy plugin add`.

## Development

```bash
python3 -m unittest discover -s tests -v
python3 index-icons.py
omarchy plugin validate .
```

See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/troubleshooting.md](docs/troubleshooting.md).

## Limitations

No folders, drag reordering, uninstall UI, pagination, or icon recoloring. Application
visibility follows Quickshell's desktop catalogue and `NoDisplay`; full desktop-specific
menu rules are not implemented. The icon index prioritizes user files and app/device
artwork, not complete theme inheritance. A cold startup may briefly show fallback icons.
Native gestures remain subject to libinput classification, typing suppression, and
Hyprland's recognition threshold. Three-finger dragging can take precedence over a
three-finger pinch. Five-finger gestures are not supported by the investigated native path.

## License

MIT. See [LICENSE](LICENSE).
