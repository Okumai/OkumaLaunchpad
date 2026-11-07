import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Hyprland
import qs.Commons as Commons

Item {
    id: root
    property var shell: null
    readonly property string pluginId: "okuma.dev_launchpad4omarchy"
    readonly property string pluginDirectory: decodeURIComponent(Qt.resolvedUrl(".").toString().replace(/^file:\/\//, ""))
    property var settings: ({})
    readonly property string fontFamily: shell && shell.bar ? shell.bar.fontFamily : Commons.Style.font.family
    readonly property color foreground: Commons.Color.menu.text
    readonly property color muted: Commons.Color.muted
    readonly property color selectedBackground: Commons.Color.menu.selectedBackground
    readonly property color selectedBorder: Commons.Color.menu.selectedBorder
    function numberSetting(key, fallback, low, high) {
        const value = settings[key];
        return typeof value === "number" && isFinite(value) ? Math.max(low, Math.min(high, value)) : fallback;
    }
    FileView {
        path: (Quickshell.env("XDG_CONFIG_HOME") || Quickshell.env("HOME") + "/.config") + "/omarchy/shell.json"
        watchChanges: true
        onFileChanged: reload()
        onLoaded: {
            try { root.settings = (JSON.parse(text()).plugins || []).find(p => p.id === root.pluginId) || {}; }
            catch (error) { console.warn("OkumarchyLaunchpad settings:", error); }
        }
    }
    Connections {
        target: DesktopEntries.applications
        function onValuesChanged() { iconRefresh.restart(); }
    }
    Timer { id: iconRefresh; interval: 750; onTriggered: if (!iconScan.running) iconScan.running = true }
    property bool opened: false
    // Keep the surface mapped until the short exit transition has finished.
    property real reveal: opened ? 1 : 0
    Behavior on reveal {
        NumberAnimation {
            // The compositor fade is disabled for this surface in looknfeel.lua.
            duration: root.opened ? root.numberSetting("openDuration", 90, 0, 500) : root.numberSetting("closeDuration", 70, 0, 500)
            easing.type: Easing.OutCubic
        }
    }
    property string query: ""
    property var iconIndex: ({})
    readonly property string fallbackIcon: Qt.resolvedUrl("fallback-app.svg").toString()
    Process {
        id: iconScan
        command: ["python3", root.pluginDirectory + "index-icons.py"]
        running: true
        stdout: StdioCollector {
            onStreamFinished: {
                try { root.iconIndex = JSON.parse(text); }
                catch (error) { console.warn("Could not read icon index:", error); }
            }
        }
    }
    // Local touchpad/wheel gain; does not change other applications.
    readonly property real scrollSensitivity: numberSetting("scrollSensitivity", 3, 0.25, 10)
    property var entries: {
        const q = query.trim().toLocaleLowerCase();
        return DesktopEntries.applications.values.filter(e => !e.noDisplay &&
            (!q || [e.name, e.genericName, e.comment, (e.keywords || []).join(" ")]
                .join(" ").toLocaleLowerCase().includes(q)))
            .sort((a, b) => a.name.localeCompare(b.name));
    }

    function open(payloadJson) {
        if (opened) return;
        if (!iconScan.running) iconScan.running = true;
        const monitor = Hyprland.focusedMonitor;
        const screens = Quickshell.screens;
        panel.screen = screens.find(s => monitor && s.name === monitor.name) || screens[0];
        query = "";
        search.text = "";
        grid.currentIndex = 0;
        grid.positionViewAtBeginning();
        opened = true;
        Qt.callLater(() => search.forceActiveFocus());
    }
    function close() { opened = false; }
    function dismiss() {
        close();
        if (shell) shell.hide(pluginId);
    }
    function status() { return opened ? "open" : "closed"; }
    function appCount() { return String(entries.length); }
    function iconDiagnostics() {
        const apps = DesktopEntries.applications.values.filter(e => !e.noDisplay);
        return JSON.stringify({indexed: Object.keys(iconIndex).length, apps: apps.length,
            fallback: apps.filter(e => iconSource(e.icon) === fallbackIcon).map(e => ({name: e.name, icon: e.icon}))});
    }
    function launch(entry) {
        if (!entry) return;
        // Use the desktop-entry resolver, preserving terminal apps, field codes and quoting.
        Quickshell.execDetached(["uwsm-app", "--", "gtk-launch", entry.id + ".desktop"]);
        dismiss();
    }
    function moveSelection(delta) {
        grid.currentIndex = Math.max(0, Math.min(entries.length - 1, grid.currentIndex + delta));
        grid.positionViewAtIndex(grid.currentIndex, GridView.Contain);
    }
    function iconSource(icon) {
        const value = String(icon || "");
        if (value.startsWith("/")) return "file://" + value;
        if (value.startsWith("file://") || value.startsWith("image://")) return value;
        // File URLs work even when Qt has cached an absent/invalid icon theme.
        return root.iconIndex[value] || Quickshell.iconPath(value, true) || root.fallbackIcon;
    }

    PanelWindow {
        id: panel
        visible: root.opened || root.reveal > 0
        anchors { top: true; bottom: true; left: true; right: true }
        exclusionMode: ExclusionMode.Ignore
        color: "transparent"
        WlrLayershell.namespace: "okumarchy-launchpad"
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.keyboardFocus: root.opened ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.None

        Image {
            anchors.fill: parent
            opacity: root.reveal
            source: "file://" + (Quickshell.env("XDG_STATE_HOME") || Quickshell.env("HOME") + "/.local/state") + "/omarchy/current/background"
            fillMode: Image.PreserveAspectCrop
            asynchronous: true
        }
        Rectangle { anchors.fill: parent; color: Commons.Color.menu.background; opacity: root.reveal * root.numberSetting("backgroundOpacity", 0.94, 0.3, 1) }
        MouseArea { anchors.fill: parent; enabled: root.opened; onClicked: root.dismiss() }

        Item {
            id: content
            anchors.fill: parent
            anchors.margins: Math.max(20, Math.min(panel.width, panel.height) * 0.03)
            enabled: root.opened
            opacity: root.reveal
            scale: 0.975 + 0.025 * root.reveal

            Rectangle {
                id: searchBox
                anchors.top: parent.top
                anchors.horizontalCenter: parent.horizontalCenter
                width: Math.min(root.numberSetting("searchWidth", 300, 160, 600), parent.width)
                height: 30
                radius: 10
                color: "#10ffffff"
                border.color: "#1cffffff"
                TextField {
                    id: search
                    anchors.fill: parent
                    leftPadding: 12
                    rightPadding: 12
                    topPadding: 4
                    bottomPadding: 4
                    placeholderText: "Search apps..."
                    placeholderTextColor: root.muted
                    color: root.foreground
                    font.family: root.fontFamily
                    font.pixelSize: 13
                    background: Item {}
                    selectByMouse: true
                    onTextChanged: {
                        root.query = text;
                        grid.currentIndex = 0;
                        grid.positionViewAtBeginning();
                    }
                    onAccepted: root.launch(root.entries[grid.currentIndex])
                    Keys.onEscapePressed: root.dismiss()
                    Keys.onDownPressed: root.moveSelection(grid.columns)
                    Keys.onUpPressed: root.moveSelection(-grid.columns)
                    Keys.onLeftPressed: event => {
                        if (text.length === 0) root.moveSelection(-1);
                        else event.accepted = false;
                    }
                    Keys.onRightPressed: event => {
                        if (text.length === 0) root.moveSelection(1);
                        else event.accepted = false;
                    }
                    Keys.onTabPressed: root.moveSelection(1)
                    Keys.onBacktabPressed: root.moveSelection(-1)
                }
            }

            GridView {
                id: grid
                anchors.top: searchBox.bottom
                anchors.topMargin: 12
                anchors.bottom: footer.top
                anchors.bottomMargin: 8
                anchors.horizontalCenter: parent.horizontalCenter
                width: Math.min(1120, parent.width)
                property int columns: Math.max(1, Math.floor(width / root.numberSetting("cellSize", 140, 100, 220)))
                cellWidth: width / columns
                cellHeight: root.numberSetting("cellSize", 140, 100, 220)
                clip: true
                model: root.entries
                boundsBehavior: Flickable.StopAtBounds
                currentIndex: 0
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                WheelHandler {
                    // Handle the event once, including touchpad momentum events.
                    // Pixel deltas preserve smooth scrolling and the system's direction.
                    target: null
                    acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
                    onWheel: event => {
                        const dy = event.pixelDelta.y !== 0
                            ? event.pixelDelta.y : event.angleDelta.y / 120 * 60;
                        if (dy !== 0) {
                            grid.cancelFlick();
                            const top = grid.originY;
                            const bottom = top + Math.max(0, grid.contentHeight - grid.height);
                            grid.contentY = Math.max(top, Math.min(bottom,
                                grid.contentY - dy * root.scrollSensitivity));
                        }
                        event.accepted = true;
                    }
                }
                delegate: Item {
                    id: tile
                    required property var modelData
                    required property int index
                    width: grid.cellWidth
                    height: grid.cellHeight
                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: 6
                        radius: 18
                        color: mouse.containsMouse || tile.index === grid.currentIndex ? root.selectedBackground : "transparent"
                        border.color: tile.index === grid.currentIndex ? root.selectedBorder : "transparent"
                        Behavior on color { ColorAnimation { duration: 100 } }
                    }
                    Image {
                        id: icon
                        anchors.top: parent.top
                        anchors.topMargin: 17
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: root.numberSetting("iconSize", 64, 24, 80)
                        height: width
                        source: root.iconSource(tile.modelData.icon)
                        onStatusChanged: if (status === Image.Error && source.toString() !== root.fallbackIcon) source = root.fallbackIcon
                        sourceSize.width: 128
                        sourceSize.height: 128
                        fillMode: Image.PreserveAspectFit
                    }
                    Text {
                        anchors.top: icon.bottom
                        anchors.topMargin: 10
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: parent.width - 18
                        text: tile.modelData.name
                        color: root.foreground
                        font.family: root.fontFamily
                        font.pixelSize: 13
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.Wrap
                        maximumLineCount: 2
                        elide: Text.ElideRight
                    }
                    MouseArea {
                        id: mouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.launch(tile.modelData)
                    }
                    ToolTip.visible: mouse.containsMouse
                    ToolTip.delay: 800
                    ToolTip.text: tile.modelData.name
                }
                Text {
                    anchors.centerIn: parent
                    visible: grid.count === 0
                    text: "No matching apps"
                    color: root.muted
                    font.family: root.fontFamily
                    font.pixelSize: 18
                }
            }
            Text {
                id: footer
                anchors.bottom: parent.bottom
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.entries.length + " apps  |  Scroll to browse  |  Esc to close"
                color: root.muted
                font.family: root.fontFamily
                font.pixelSize: 11
            }
        }
    }
}
