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
                    required property string title_
                    required property bool checked_

                    title: title_
                    checked: checked_
                    width: tabsArea.tabWidth
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
                    toolTip: qsTr("新建标签页")
                    onClicked: qmlapp.tab.addNavi()
                }
            }
        }

    }

    Item {
        Layout.preferredWidth: size_.hTabBarHeight
        Layout.fillHeight: true

        IconButton {
            anchors.fill: parent
            anchors.margins: 4
            icon_: qmlapp.tab.barIsLock ? "lock" : "lock_open"
            color: qmlapp.tab.barIsLock ? theme.bgColor : theme.textColor
            bgColor_: qmlapp.tab.barIsLock ? theme.coverColor4 : "transparent"
            bgHoverColor_: theme.coverColor2
            onClicked: qmlapp.tab.barIsLock = !qmlapp.tab.barIsLock
            toolTip: qmlapp.tab.barIsLock ? qsTr("解除标签栏锁定") : qsTr("锁定标签栏")
        }
    }
}
