-- Optional Hyprland Lua integration. Review existing bindings before adding.
-- Do not register these alongside the earlier standalone Launchpad bindings.
-- Existing workspace swipes and three-finger drag configuration are untouched.

-- Use only the launcher's own transition, not an additional compositor fade.
hl.layer_rule({ match = { namespace = "^okumarchy-launchpad$" }, no_anim = true, animation = "none" })

local fired = false
local function pinch(e)
  if fired or not e.scale then return end
  local command
  if e.scale <= 0.90 then
    command = "omarchy-shell shell summon launchpad.okuma.dev '{}'"
  elseif e.scale >= 1.10 then
    command = "omarchy-shell shell hide launchpad.okuma.dev"
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

-- Hyprland 0.56.2 calls expanding distance "pinchin". Verify on other versions.
-- The recognizer has already applied its native threshold before start runs.
hl.gesture({
  fingers = 3,
  direction = "pinchin",
  action = {
    start = function(e)
      if e.scale and e.scale > 1 then
        hl.exec_cmd("omarchy-shell shell hide launchpad.okuma.dev")
      end
    end,
  },
})
