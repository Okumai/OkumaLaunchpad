# Desktop integration

## Native gestures

Installing or enabling an Omarchy plugin does not install compositor gesture bindings.
On each device, run `python3 /path/to/plugin/setup-gestures.py install` after enabling
the plugin. The setup tool backs up the existing user input.lua, adds a managed block,
reloads Hyprland, and checks configuration errors, restoring the original on failure.
Use `remove` to remove only that block. Run `doctor.py` for non-privileged diagnostics.
Custom layouts can use `--config /path/to/loaded/input.lua`; `--no-reload` is for offline
editing and requires manual reload/validation. Included configuration conflicts must
still be reviewed manually. The tool does not prove hardware gesture support.

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

The dock's default Applications button continues to use the standard Omarchy menu.
To use this launcher, replace that pin in the dock's configured `pinned` list with:

```json
{
  "key": "launchpad",
  "name": "Applications",
  "icon": "view-app-grid-symbolic",
  "shellPlugin": "okuma.dev_launchpad4omarchy"
}
```

Preserve the other dock pins and settings. This uses the dock's existing public
shell-plugin activation support; no dock source changes are required.

## Removing the plugin

Remove its optional gesture bindings and layer rule, reload and validate Hyprland,
then disable the plugin. Use `omarchy plugin remove okuma.dev_launchpad4omarchy` for a managed
installation. No global theme, packaged file, or system service needs restoration.
