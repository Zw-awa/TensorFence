import QtQuick 2.15

Button_ {
    id: root

    property string icon_: ""
    property color color: theme.subTextColor
    property real margins: Math.max(2, size_.smallSpacing * 0.6)

    contentItem: Item {
        Icon_ {
            anchors.fill: parent
            anchors.margins: root.margins
            icon: root.icon_
            color: root.color
        }
    }
}
