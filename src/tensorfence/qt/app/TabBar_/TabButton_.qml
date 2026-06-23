pragma ComponentBehavior: Bound

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

import "../Widgets"

Button {
    id: root

    property string title: ""
    property int index: -1

    height: size_.hTabBarHeight
    checkable: false
    hoverEnabled: true
    z: checked ? 10 : 0

    signal dragStart(int index)
    signal dragFinish(int index)
    signal dragMoving(int index, int x)

    contentItem: RowLayout {
        anchors.fill: parent
        anchors.leftMargin: size_.smallSpacing
        anchors.rightMargin: size_.smallSpacing
        spacing: size_.smallSpacing

        Text_ {
            Layout.fillWidth: true
            text: root.title
            elide: Text.ElideRight
            color: root.checked ? theme.textColor : theme.subTextColor
            font.bold: root.checked
        }

        IconButton {
            visible: !qmlapp.tab.barIsLock && (root.hovered || root.checked)
            Layout.preferredWidth: size_.line * 1.2
            Layout.preferredHeight: size_.line * 1.2
            icon_: "no"
            color: theme.subTextColor
            bgHoverColor_: theme.coverColor1
            onClicked: qmlapp.tab.closeTabPage(root.index)
        }
    }

    background: Rectangle {
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
        id: dragArea
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.MiddleButton
        drag.target: qmlapp.tab.barIsLock ? undefined : root
        drag.axis: Drag.XAxis
        drag.threshold: 24
        property bool dragging: drag.active

        onPressed: function(mouse) {
            if (mouse.button === Qt.LeftButton) {
                qmlapp.tab.showTabPage(root.index)
            }
        }
        onClicked: function(mouse) {
            if (mouse.button === Qt.MiddleButton && !qmlapp.tab.barIsLock) {
                qmlapp.tab.closeTabPage(root.index)
            }
        }
        onDraggingChanged: {
            if (dragging) {
                root.opacity = 0.7
                dragStart(root.index)
            } else {
                root.opacity = 1
                dragFinish(root.index)
            }
        }
        onPositionChanged: {
            if (dragging) {
                dragMoving(root.index, root.x)
            }
        }
    }
}
