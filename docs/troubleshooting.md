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

## Dock opens the system launcher instead

The stock Dock's button has a private AppGrid; changing `omarchy.menu` pins cannot
replace it. Update the installed Launchpad source (not only the checkout), then run:

```bash
python3 ~/.config/omarchy/plugins/okuma.dev_launchpad4omarchy/setup-docks.py install
omarchy-shell omarchy.dock launchpadIntegration
```

The second command must return `okuma-launchpad-v1`. If setup rejects a changed stock
source, custom Dock clone or locally edited managed files, review the conflict rather
than deleting ownership state or patching `/usr/share/omarchy/`. The adapter is a
snapshot: refresh it after Omarchy updates. An interrupted rescan is checked against
the actual live marker; persistent failure is not treated as success. Only deliberately
restart the shared shell if logs show stale/cached QML. The adapter retains stock Dock
visibility on floating workspaces; it does not make that Dock appear everywhere.

For OkumaDock, update its actual installed source too. Its status should report
`launcherPlugin: okuma.dev_launchpad4omarchy` after integration. Explicit custom pins and alternative launcher preferences
are preserved, so inspect them if an entry still launches something else.
Installing OkumaDock later uses its default `auto`; rerun Dock setup to require
Launchpad. The strict helper reports a disabled/missing Launchpad instead of opening
another launcher. Other docks must pin `Okuma Launchpad` or configure the documented
activation command; there is no universal interception of a hardcoded internal grid.
Run `setup-docks.py remove` before uninstalling Launchpad to restore previous routing.

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

## Works on the original machine, not another device

Run `python3 /path/to/OkumarchyLaunchpad/doctor.py` on each machine (pass the same
`--config` and `--fingers` as the installer). Fix `unknown` plugin status first;
that is not a touchpad failure. `hyprctl devices` lists pointer devices but does not
prove pinch support. The doctor also reports udev touchpad classification, the exact
live binding marker, stale Dock versions, and old standalone Launchpad configuration.

If public IPC opens the grid but gestures do not, verify the loaded marker, conflicts
in all included files, and physical pinch recognition. Try the explicit three-finger
profile if four-finger pinch is not reported by the device. Do not grant raw input
permissions or install another gesture daemon as a first fix. See the legacy migration
and Dock update instructions in [integration.md](integration.md).

## Four-finger left/right swipe does not switch workspaces

This is Hyprland workspace integration, not Dock activation. Older setup installed
pinch only, and Omarchy's commented three-finger example is not an active binding.
Run `doctor.py` to distinguish missing managed workspace bindings, a manual binding,
wrong live options and the absence of another workspace.

For a fresh configuration after updating the source:

```bash
python3 /path/to/OkumarchyLaunchpad/setup-gestures.py install --workspaces
hyprctl configerrors
```

If setup detects an existing horizontal/swipe binding, do not add another blindly.
Review all includes and migrate only the exact manual workspace binding, or retain
it and use `install.sh --no-workspaces`. A modified-only binding does not handle an
unmodified swipe. A catch-all `swipe`, left/right focus binding or dynamic Lua may
intercept the same fingers; static checks cannot prove arbitrary Lua conflict-free.

The managed profile enables numeric neighbors and new empty workspaces. Test with
Launchpad closed, outside a remote desktop/game, no modifiers pressed, and all four
fingers touching before moving. A short/slow movement may animate then snap back
because of the swipe distance/cancellation threshold; that differs from no response.
Try a deliberate longer horizontal motion before adjusting sensitivity. Natural
scroll direction does not select the workspace gesture's inverse direction.
Do not disable dragging/typing suppression or bypass shortcut inhibition globally.
`--fingers 3` only changes Launchpad pinch; it does not fix missing four-finger swipe
events from hardware. See [integration.md](integration.md) for migration and tests.

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
