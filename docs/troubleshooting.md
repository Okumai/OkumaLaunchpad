# Troubleshooting

## Plugin does not open

```bash
omarchy plugin validate /path/to/OkumarchyLaunchpad
omarchy plugin list --json
omarchy-shell shell rescanPlugins
omarchy-shell shell summon okuma.dev_launchpad4omarchy '{}'
omarchy-shell shell call okuma.dev_launchpad4omarchy status ''
```

The plugin must be enabled and the current Omarchy shell must support keep-loaded
panels and `qs.Commons`. Inspect the running shell's Quickshell logs for QML errors.
Only restart the shell when necessary; it also hosts the bar and other plugins.

## Icons are blank or generic

```bash
python3 /path/to/OkumarchyLaunchpad/index-icons.py
omarchy-shell shell call okuma.dev_launchpad4omarchy iconDiagnostics ''
```

The asynchronous index scans XDG icon directories and pixmaps on startup, on app
catalogue changes, and when opening. A cold start may briefly show generic artwork.
An absent selected icon theme can break Qt lookup even when application icon files
exist; direct file URLs bypass that issue. The bundled fallback also handles missing
or unreadable artwork. The index intentionally excludes toolbar/action icons, which
can share application names. It is not a complete icon-theme inheritance engine.

## Gestures do not respond

Test manual summon/hide first. Confirm that only one set of Launchpad bindings is
registered. Native recognition requires a physical touchpad test. Put fingers down
together without pressing the touchpad button. Three-finger dragging and typing
suppression can prevent pinch recognition. Do not disable those features globally
without considering palm rejection and everyday dragging behavior.

## Opening feels slow

Use the namespace-specific no-animation rule from `examples/hyprland.lua` to avoid
stacking the compositor's fade with the plugin's transition. Tune `openDuration`
and `closeDuration`; zero disables the respective transition. Those settings do
not change libinput classification or Hyprland's native recognition threshold.

## Theme or font is wrong

The plugin reads shared Omarchy menu colors and the active bar font. Confirm that
OkumarchyDock and built-in menus receive the expected theme. Application icon colors
are not recolored by this plugin. A missing wallpaper does not prevent the grid
from working; the theme-colored overlay remains available.
