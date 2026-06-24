pragma ComponentBehavior: Bound

import QtQuick 2.15
import QtQuick.Layouts 1.15

import "../Widgets"

Item {
    id: root

    property string title: ""
    property int pageIndex: -1
    property bool checked: false
    readonly property bool hovered: tabMouseArea.containsMouse || closeButton.hovered

    implicitHeight: size_.hTabBarHeight
    z: checked ? 10 : 0

    Rectangle {
        anchors.fill: parent
        radius: size_.btnRadius
        color: root.checked ? theme.bgColor : (root.hovered ? theme.coverColor1 : "transparent")
        border.width: root.checked ? 1 : 0
        border.color: theme.coverColor2

        Rectangle {
            visible: !root.checked
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            width: 1
            height: size_.line
            color: theme.coverColor3
        }
    }

    MouseArea {
        id: tabMouseArea
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.MiddleButton

        onPressed: function(mouse) {
            if (mouse.button === Qt.LeftButton) {
                qmlapp.tab.showTabPage(root.pageIndex)
            }
        }
        onClicked: function(mouse) {
            if (mouse.button === Qt.MiddleButton && !qmlapp.tab.barIsLock) {
                qmlapp.tab.closeTabPage(root.pageIndex)
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: size_.smallSpacing
        anchors.rightMargin: size_.smallSpacing
        spacing: size_.smallSpacing

        Text_ {
            Layout.fillWidth: true
            text: root.title.length > 0 ? root.title : qsTr("未命名")
            elide: Text.ElideRight
            color: root.checked ? theme.textColor : theme.subTextColor
            font.bold: root.checked
            verticalAlignment: Text.AlignVCenter
        }

        IconButton {
            id: closeButton
            visible: !qmlapp.tab.barIsLock && (root.hovered || root.checked)
            Layout.preferredWidth: size_.line * 1.2
            Layout.preferredHeight: size_.line * 1.2
            icon_: "close"
            color: theme.subTextColor
            bgHoverColor_: theme.coverColor1
            toolTip: qsTr("关闭标签页")
            onClicked: qmlapp.tab.closeTabPage(root.pageIndex)
        }
    }
}
