# Desktop integration

## Native gestures

Installing or enabling an Omarchy plugin does not install compositor gesture bindings.
On each device, run `python3 /path/to/plugin/setup-gestures.py install` after enabling
the plugin. The setup tool backs up the existing user input.lua, adds a managed block,
reloads Hyprland, and checks configuration errors, restoring the original on failure.
Use `remove` to remove only that block. Run `doctor.py` for non-privileged diagnostics.
Custom layouts can use `--config /path/to/loaded/input.lua`; `--no-reload` is for offline
editing and requires manual reload/validation. Included configuration conflicts must
still be reviewed manually. The tool checks the Lua API before writing, clears a live
marker, reloads, and asserts that the exact installed managed block executed. This also
runs on repeated installation, preventing a stale or unloaded file from passing validation.
The tool does not prove hardware gesture support.

For devices that recognize three-finger but not four-finger pinch, pass `--fingers 3`
to `install.sh` or `setup-gestures.py install`. That profile opens inward and closes
outward with three fingers, registering only one pinch callback. It does not silently
disable three-finger dragging, typing suppression, or other touchpad preferences.

Alternatively, review `examples/hyprland.lua` and add its rules manually to your user
Hyprland Lua configuration. Back up the affected files first.
Do not add duplicate bindings for the same finger count and direction. Validate:

```bash
hyprctl reload
hyprctl configerrors
```

Four-finger pinching opens; three/four-finger spreading closes. Callbacks fire at
recognition, not release. Commands are idempotent; a four-finger gesture fires once.
Hyprland 0.56.2 gates pinch callbacks until distance changes by about 10%. A lower
Lua threshold cannot bypass that gate. Both bindings use generic `pinch` callbacks
and read scale directly, avoiding version-dependent inward/outward direction names. libinput 1.32's investigated path supports
at most four fingers. A three-finger movement classified as dragging will not emit
a pinch event. No privileged input reader or additional device permissions are used.

The layer rule only disables compositor animations for `okumarchy-launchpad`.
The plugin retains its own short transition. It does not affect dock or bar layers.

The plugin lives inside the Omarchy shell and needs no separate autostart entry.
Do not configure another launcher with the same gesture bindings.

## Four-finger horizontal workspace swipes

Workspace switching belongs to Hyprland, not the Dock or Launchpad QML. Earlier
installations installed pinch only; a working reference machine could still depend
on a manual `hl.gesture({ fingers = 4, direction = "horizontal", action = "workspace" })`
in its user input.lua. Omarchy's input template only contains a commented three-finger
example, so installing plugins on another machine did not reproduce that behavior.

The full installer now includes workspace integration by default:

```bash
./install.sh
# Keep an existing manual workspace setup, installing only pinch:
./install.sh --no-workspaces
# Gesture-only integration (no shell/plugin changes):
python3 setup-gestures.py install --workspaces
```

The separate workspace block uses Hyprland's native continuous `workspace` action,
not shell commands on every motion event. `workspace_swipe_use_r = true` and
`workspace_swipe_create_new = true` permit adjacent numeric workspaces even when
empty. Without a target workspace, a gesture may appear to do nothing. No distance,
speed, inverse direction, three-finger dragging, typing suppression or bar settings
are changed. `--fingers 3` affects pinch only, not this four-finger workspace binding.

Backups, exact live-marker validation and rollback apply to both blocks. Effective
workspace options are checked too; later overrides cause validation to fail instead
of silently changing the intended profile. Obvious existing four-finger horizontal,
left/right or catch-all `swipe` bindings in the selected file are rejected before
installation. Conflicting includes are normally detected by Hyprland on reload and
rolled back. Static inspection is conservative, not a complete Lua interpreter;
review dynamic bindings, custom includes and modified gestures manually.

To migrate an existing manual binding, back up the config, remove only its exact
horizontal workspace binding (and review earlier workspace options), then run setup
with `--workspaces`. Never delete unrelated up/down, pinch or three-finger bindings.
Alternatively, keep the manual configuration and pass `--no-workspaces` on every full
installer run. Plain `setup-gestures.py install` also preserves the existing workspace
block. `setup-gestures.py remove` removes both managed blocks, not manual bindings.

Test on the desktop with Launchpad closed and no modifier keys held. Put all four
fingers down before sliding horizontally, move far enough, then release. Workspaces
should follow continuously and commit rather than snap back; small gestures can
legitimately cancel. Remote desktops/games may inhibit shortcuts. Check both sides,
an empty adjacent workspace, multi-monitor behavior, pinch, vertical bar gestures,
and login/reboot recovery separately. Configuration checks cannot prove physical
four-finger events are emitted by a particular touchpad.

## Built-in Dock and other Dock entry points

The stock `omarchy.dock` button opens a private `AppGrid`, not `omarchy.menu`.
Changing a menu pin alone therefore cannot replace it. The full installer creates
`okuma.dev_launchpad_dock_bridge`, a user-owned Dock clone with `clonedFrom:
omarchy.dock`. Only `openApps()` and the `apps` IPC method are adapted; settings,
pins, visibility and other behavior stay stock. Omarchy's clone resolver routes
`omarchy-shell omarchy.dock apps` to this adapter. The stock plugin is disabled
while its replacement is enabled; nothing under `/usr/share/omarchy/` is edited.

```bash
python3 ~/.config/omarchy/plugins/okuma.dev_launchpad4omarchy/setup-docks.py install
python3 ~/.config/omarchy/plugins/okuma.dev_launchpad4omarchy/setup-docks.py remove
```

Installation backs up `shell.json` and earlier owned files under
`$XDG_STATE_HOME/okuma-launchpad` (default `~/.local/state/okuma-launchpad`). Unknown
stock source layouts, enabled custom stock-Dock clones and locally edited managed
files are rejected. Ownership hashes and original preferences are recorded there;
do not delete that state before uninstalling. Repeated setup refreshes the clone
from the current packaged Dock. Refresh after Omarchy Dock updates. It verifies a
live adapter marker, but does not force-restart the shared shell if QML is cached.
Failures during late live validation leave the backed-up integration available for
inspection/removal; they are not reported as success. Use `--no-dock-integration`
with `install.sh` to skip all these changes.

The generated `okuma-launchpad.desktop` uses the installed activation helper; pin
**Okuma Launchpad** in other configurable docks, or configure:

```bash
python3 ~/.config/omarchy/plugins/okuma.dev_launchpad4omarchy/activate-launchpad.py toggle
```

The helper supports `show` and `hide` too, validates actual `open`/`closed` state,
and fails visibly without opening another launcher. Arbitrary third-party docks
with a hardcoded internal grid need their own adapter; matching an icon's name is
not a universal interception mechanism. A desktop entry is generated on each
machine, with quoted local paths rather than a repository author's absolute path.
The adapter keeps the original Dock's floating-workspace visibility and does not
force-enable a previously disabled Dock on other layouts.

## OkumarchyDock integration

Update OkumarchyDock as well as Launchpad. The updated Dock resolves its Applications
button on every click. Its `auto` mode prefers a responding Launchpad plugin and
otherwise opens the standard Omarchy Applications menu. The full Launchpad installer
changes an already-configured OkumaDock's `launcherPlugin` from `auto` (or unset) to
`okuma.dev_launchpad4omarchy`, requiring Launchpad instead of allowing fallback.
An explicitly selected alternative launcher is preserved; choose Launchpad manually
to replace that preference. Removing Dock integration restores
the prior preference only if the installed value was not subsequently changed. Installing/enabling Launchpad after Dock works
without rebuilding pins or restarting the shell. Disabled/missing Launchpad is not
mistaken for a successful activation merely because IPC exited zero.

Saved default Applications pins and old `[/home/user/.local/bin/launchpad, toggle]`
pins are routed through the same public IPC helper; arbitrary custom launchers are
preserved. A new portable pin is:

```json
{"key":"launcher","name":"Applications","icon":"view-app-grid-symbolic","classes":[],"launcher":true}
```

To require Launchpad instead of allowing fallback, use:

```json
{
  "key": "launchpad",
  "name": "Applications",
  "icon": "view-app-grid-symbolic",
  "shellPlugin": "okuma.dev_launchpad4omarchy"
}
```

Preserve the other dock pins and settings. Dock's `launcherPlugin` setting accepts
`auto` (default), `okuma.dev_launchpad4omarchy` (required), or `omarchy.menu` (always
built-in). Installing OkumaDock later retains its own default `auto`; set its preference
to Launchpad or rerun `setup-docks.py install` to require it. Other docks must explicitly
configure the activation command or desktop entry above;
there is no universal third-party Dock integration API.

## Migrating the old independent Launchpad

A working `~/.local/bin/launchpad` script on one device does not imply this plugin
is installed. Run `doctor.py`: plugin status must be `open` or `closed`, not `unknown`.
The old implementation uses `~/.config/quickshell/launchpad/shell.qml` and a separate
`qs -c launchpad` process. Do not copy its absolute paths to another user/device.

Back up user `hypr/input.lua`, `hypr/autostart.lua`, and `omarchy/shell.json`. Remove
only the old Launchpad pinch callbacks and its `qs -c launchpad` autostart entry;
retain workspace swipes, bar gestures, and personal input preferences. Close the old
panel and terminate only its identified process, not the shared Omarchy shell. Then
run the plugin installer. It intentionally refuses unmanaged duplicate pinch blocks
rather than deleting arbitrary Lua. Replace old Dock launcher commands with the
portable `launcher: true` pin when convenient (updated Dock also handles them live).

## Removing the plugin

Run `setup-docks.py remove` before disabling/removing Launchpad so the stock Dock and
previous OkumaDock preference are restored and the desktop entry is removed. Then
remove its optional gesture bindings and layer rule, reload and validate Hyprland,
and disable the plugin. Use `omarchy plugin remove okuma.dev_launchpad4omarchy` for a managed
installation. No global theme, packaged file, or system service needs restoration.
