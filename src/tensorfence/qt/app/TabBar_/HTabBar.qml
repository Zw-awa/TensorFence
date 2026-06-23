pragma ComponentBehavior: Bound

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

import "../Widgets"

RowLayout {
    id: root
    anchors.fill: parent
    spacing: 0

    Item {
        Layout.preferredWidth: size_.hTabBarHeight
        Layout.fillHeight: true

        IconButton {
            id: pinButton
            anchors.fill: parent
            anchors.margins: 4
            icon_: "pin"
            color: mainWindowRoot.isMainWindowTop ? theme.bgColor : theme.textColor
            bgColor_: mainWindowRoot.isMainWindowTop ? theme.coverColor4 : "transparent"
            bgHoverColor_: theme.coverColor2
            onClicked: mainWindowRoot.isMainWindowTop = !mainWindowRoot.isMainWindowTop
            toolTip: qsTr("窗口置顶")
        }
    }

    Rectangle {
        id: tabsArea
        Layout.fillWidth: true
        Layout.fillHeight: true
        color: "transparent"

        property real tabWidth: Math.min(size_.line * 9, Math.max(120, (width - (qmlapp.tab.barIsLock ? 0 : addButtonWrap.width)) / Math.max(1, barManager.model.count)))
        property var slotCenters: []

        function captureSlots() {
            slotCenters = []
            for (let i = 0; i < barManager.model.count; i++) {
                const item = barManager.itemAt(i)
                if (item) {
                    slotCenters.push(item.x + item.width / 2)
                }
            }
        }

        function dropIndexFor(index) {
            const item = barManager.itemAt(index)
            if (!item || slotCenters.length === 0) {
                return index
            }
            const center = item.x + item.width / 2
            let candidate = slotCenters.length - 1
            for (let i = 0; i < slotCenters.length; i++) {
                if (center < slotCenters[i]) {
                    candidate = i
                    break
                }
            }
            return candidate
        }

        MouseArea {
            anchors.fill: parent
            onClicked: {
                if (!qmlapp.tab.barIsLock) {
                    qmlapp.tab.addNavi()
                }
            }
        }

        Row {
            id: tabsRow
            spacing: -1

            BarManager {
                id: barManager

                delegate: TabButton_ {
                    title: title_
                    checked: checked_
                    index: index_
                    width: tabsArea.tabWidth
                    onDragStart: {
                        tabsArea.captureSlots()
                    }
                    onDragFinish: function(index) {
                        const target = tabsArea.dropIndexFor(index)
                        qmlapp.tab.moveTabPage(index, target)
                        dragMarker.visible = false
                        x = 0
                    }
                    onDragMoving: function(index, x) {
                        dragMarker.visible = true
                        const target = tabsArea.dropIndexFor(index)
                        const ref = barManager.itemAt(Math.min(target, Math.max(0, barManager.model.count - 1)))
                        if (ref) {
                            dragMarker.x = ref.x
                        }
                    }
                }
            }

            Item {
                id: addButtonWrap
                width: qmlapp.tab.barIsLock ? 0 : size_.hTabBarHeight
                height: size_.hTabBarHeight

                IconButton {
                    visible: !qmlapp.tab.barIsLock
                    anchors.fill: parent
                    anchors.margins: 4
                    icon_: "add"
                    color: theme.textColor
                    bgHoverColor_: theme.coverColor1
                    onClicked: qmlapp.tab.addNavi()
                }
            }
        }

        Rectangle {
            id: dragMarker
            visible: false
            y: 3
            width: tabsArea.tabWidth
            height: size_.hTabBarHeight - 6
            radius: size_.btnRadius
            color: theme.coverColor1
            border.width: 1
            border.color: theme.coverColor2
        }
    }

    Item {
        Layout.preferredWidth: size_.hTabBarHeight
        Layout.fillHeight: true

        IconButton {
            anchors.fill: parent
            anchors.margins: 4
            icon_: "lock"
            color: qmlapp.tab.barIsLock ? theme.bgColor : theme.textColor
            bgColor_: qmlapp.tab.barIsLock ? theme.coverColor4 : "transparent"
            bgHoverColor_: theme.coverColor2
            onClicked: qmlapp.tab.barIsLock = !qmlapp.tab.barIsLock
            toolTip: qsTr("锁定标签栏")
        }
    }
}
