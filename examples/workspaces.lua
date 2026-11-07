-- Optional native continuous four-finger workspace swipe.
-- Keep three-finger dragging, vertical bar gestures and pinch bindings unchanged.
-- Numeric neighbors include empty workspaces, matching the reference desktop.
hl.config({
  gestures = {
    workspace_swipe_use_r = true,
    workspace_swipe_create_new = true,
  },
})
hl.gesture({ fingers = 4, direction = "horizontal", action = "workspace" })
