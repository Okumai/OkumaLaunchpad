# OkumarchyLaunchpad

A fast, theme-aware fullscreen application launcher for Omarchy's Quickshell desktop.

Project: https://github.com/Okumai/Launchpad

Author: ŌKUMA | Plugin ID: `okuma.dev_launchpad4omarchy`

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

### Recommended: managed installation with default gestures

```bash
omarchy plugin add https://github.com/Okumai/Launchpad.git
# Review the installed source before enabling it.
bash ~/.config/omarchy/plugins/okuma.dev_launchpad4omarchy/install.sh
```

The installer validates and enables the plugin, checks that it responds, then installs
and validates gesture bindings by default. It explains the target files and requests
confirmation. Plugins run unsandboxed as your user. No packaged files are modified.
The `omarchy plugin add` command alone cannot run this integration step automatically.

### Local checkout

```bash
cd /path/to/OkumarchyLaunchpad
./install.sh
```

A new local installation is a snapshot without Git metadata. An existing target is
reused, never overwritten. For Git-managed updates, prefer the managed installation
above. Local snapshot updates must be reviewed and applied separately.

Options:

```bash
./install.sh --no-gestures   # Enable the plugin without changing touchpad bindings.
./install.sh --yes          # Explicit consent for unattended installation.
./install.sh --config ~/.config/hypr/input.lua
```

Gesture setup refuses obvious conflicting pinch bindings and backs up user config.
If gesture validation fails, that file is restored. Plugin installation/enabling steps
already completed are retained and reported; the installer is not a full transaction.
It never forces a restart of the shared Omarchy shell.

```bash
omarchy-shell shell summon okuma.dev_launchpad4omarchy '{}'
omarchy-shell shell hide okuma.dev_launchpad4omarchy
omarchy-shell shell toggle okuma.dev_launchpad4omarchy '{}'
```

If the plugin was enabled directly with `omarchy plugin add --enable`, complete setup
with `install.sh`, or run the gesture-only command on each device:

```bash
python3 ~/.config/omarchy/plugins/okuma.dev_launchpad4omarchy/setup-gestures.py install
```

The command backs up the existing user `input.lua`, installs a managed binding block,
reloads Hyprland, and checks configuration errors. It refuses obvious duplicate pinch
bindings; review other included files too. It does not change packaged files or global
touchpad settings. The user input.lua must already be loaded by your Hyprland config.

```bash
python3 ~/.config/omarchy/plugins/okuma.dev_launchpad4omarchy/doctor.py
python3 ~/.config/omarchy/plugins/okuma.dev_launchpad4omarchy/setup-gestures.py remove
```

See [docs/integration.md](docs/integration.md) for desktop integration details.
Plugin updates do not automatically rewrite gesture bindings;
rerun `bash ~/.config/omarchy/plugins/okuma.dev_launchpad4omarchy/install.sh` after updating
to refresh the managed block without duplicating bindings. The plugin never edits
Hyprland configuration during login or hot reload. Creating this repository does not
change your desktop.

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
omarchy plugin disable okuma.dev_launchpad4omarchy
omarchy plugin enable okuma.dev_launchpad4omarchy
omarchy plugin update okuma.dev_launchpad4omarchy
omarchy-shell shell call okuma.dev_launchpad4omarchy status ''
omarchy-shell shell call okuma.dev_launchpad4omarchy iconDiagnostics ''
```

Git-managed updates require installation through `omarchy plugin add`.

## Uninstall

If optional gestures were installed, remove the managed binding block before
removing the plugin files. Use the same `--config` path used during setup:

```bash
python3 ~/.config/omarchy/plugins/okuma.dev_launchpad4omarchy/setup-gestures.py remove
omarchy plugin disable okuma.dev_launchpad4omarchy
omarchy plugin remove okuma.dev_launchpad4omarchy
```

Skip the first command if gestures were never configured. If you added the
optional layer rule or Dock integration manually, remove only those additions
as described in [integration](docs/integration.md). The gesture helper backs up,
reloads and validates the selected Hyprland configuration. Stop and resolve any
reported error before deleting the helper.

Omarchy asks for confirmation before removal. Local-copy installations in the
standard plugin directory are backed up by Omarchy; external source checkouts
are not deleted. Do not remove the entire `shell.json` or restore an old whole
Hyprland config over later user edits. Saved settings and backups are not
securely erased. No packaged files or services need restoration.

## Development

```bash
python3 -m unittest discover -s tests -v
python3 index-icons.py
omarchy plugin validate .
```

See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/troubleshooting.md](docs/troubleshooting.md).
This repository has no GitHub Actions workflows; tests run locally on your own device.
See [source publication and local testing](docs/publication.md).

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
