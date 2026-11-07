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

## OkumarchyDock integration

Update OkumarchyDock as well as Launchpad. The updated Dock resolves its Applications
button on every click: a responding Launchpad plugin is preferred; otherwise it opens
the standard Omarchy Applications menu. Installing/enabling Launchpad after Dock works
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
built-in). Other docks must explicitly configure the public toggle command above;
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

Remove its optional gesture bindings and layer rule, reload and validate Hyprland,
then disable the plugin. Use `omarchy plugin remove okuma.dev_launchpad4omarchy` for a managed
installation. No global theme, packaged file, or system service needs restoration.
