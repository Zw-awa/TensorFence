import QtQuick 2.15

Item {
    id: root

    property color color_: theme.coverColor1
    property real radius_: size_.btnRadius
    property bool hovered: false

    anchors.fill: parent

    Rectangle {
        anchors.fill: parent
        radius: root.radius_
        color: root.color_
        opacity: root.hovered ? 1 : 0

        Behavior on opacity {
            NumberAnimation { duration: 90 }
        }
    }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        onEntered: root.hovered = true
        onExited: root.hovered = false
        onPressed: function(mouse) { mouse.accepted = false }
        onReleased: function(mouse) { mouse.accepted = false }
        onClicked: function(mouse) { mouse.accepted = false }
    }
}
