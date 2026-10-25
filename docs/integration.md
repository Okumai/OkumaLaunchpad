# Desktop integration

## Native gestures

After installing and enabling the plugin, review `examples/hyprland.lua` and add its
rules to your user Hyprland Lua configuration. Back up the affected files first.
Do not add duplicate bindings for the same finger count and direction. Validate:

```bash
hyprctl reload
hyprctl configerrors
```

Four-finger pinching opens; three/four-finger spreading closes. Callbacks fire at
recognition, not release. Commands are idempotent; a four-finger gesture fires once.
Hyprland 0.56.2 gates pinch callbacks until distance changes by about 10%. A lower
Lua threshold cannot bypass that gate. Its `pinchin` name means expanding distance.
Verify that mapping on other versions. libinput 1.32's investigated path supports
at most four fingers. A three-finger movement classified as dragging will not emit
a pinch event. No privileged input reader or additional device permissions are used.

The layer rule only disables compositor animations for `okumarchy-launchpad`.
The plugin retains its own short transition. It does not affect dock or bar layers.

## Migrating from the standalone launcher

The original `~/.config/quickshell/launchpad` implementation is independent of this
plugin. Do not run both with identical gestures. Migration is deliberately manual:

1. Back up `~/.config/hypr/input.lua`, `autostart.lua`, and `looknfeel.lua`.
2. Install and enable the plugin, then test `summon` and `hide` manually.
3. Remove only the old Launchpad gesture blocks from `input.lua`; retain workspace
   swipes, bar gestures, touchpad settings, and three-finger dragging.
4. Remove the `qs -c launchpad --daemonize --no-duplicate` autostart line.
5. Replace the old `user-launchpad` layer rule with the example's
   `okumarchy-launchpad` rule and add the new gesture bindings.
6. Stop only the old instance with `qs kill -c launchpad`.
7. Reload Hyprland and check `hyprctl configerrors`.

The plugin lives inside the Omarchy shell and needs no separate autostart entry.
Keep the old files/backups until the next login has been tested. To roll back,
disable this plugin and restore only the old Launchpad blocks, not entire files
that might contain newer personal settings.

## OkumarchyDock integration

The dock's default Applications button continues to use the standard Omarchy menu.
To use this launcher, replace that pin in the dock's configured `pinned` list with:

```json
{
  "key": "launchpad",
  "name": "Applications",
  "icon": "view-app-grid-symbolic",
  "shellPlugin": "launchpad.okuma.dev"
}
```

Preserve the other dock pins and settings. This uses the dock's existing public
shell-plugin activation support; no dock source changes are required.

## Removing the plugin

Remove its optional gesture bindings and layer rule, reload and validate Hyprland,
then disable the plugin. Use `omarchy plugin remove launchpad.okuma.dev` for a managed
installation. No global theme, packaged file, or system service needs restoration.
