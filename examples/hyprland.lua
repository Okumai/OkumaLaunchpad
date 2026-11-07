-- Optional Hyprland Lua integration. Review existing bindings before adding.
-- Do not register conflicting launcher or pinch bindings.
-- Existing workspace swipes and three-finger drag configuration are untouched.

-- Use only the launcher's own transition, not an additional compositor fade.
hl.layer_rule({ match = { namespace = "^okumarchy-launchpad$" }, no_anim = true, animation = "none" })

local fired = false
local function pinch(e)
  if fired or not e.scale then return end
  local command
  if e.scale <= 0.90 then
    command = "omarchy-shell shell summon okuma.dev_launchpad4omarchy '{}'"
  elseif e.scale >= 1.10 then
    command = "omarchy-shell shell hide okuma.dev_launchpad4omarchy"
  else
    return
  end
  fired = true
  hl.exec_cmd(command)
end
hl.gesture({
  fingers = 4,
  direction = "pinch",
  action = {
    start = function(e) fired = false; pinch(e) end,
    update = pinch,
    finish = function(e) fired = false end,
  },
})

-- Read the scale rather than version-dependent pinch direction names.
-- Three-finger inward pinching never opens the launcher.
local closeFired = false
local function spread(e)
  if not closeFired and e.scale and e.scale >= 1.10 then
    closeFired = true
    hl.exec_cmd("omarchy-shell shell hide okuma.dev_launchpad4omarchy")
  end
end
hl.gesture({
  fingers = 3,
  direction = "pinch",
  action = {
    start = function(e) closeFired = false; spread(e) end,
    update = spread,
    finish = function(e) closeFired = false end,
  },
})
