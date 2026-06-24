import QtQuick 2.15

Item {
    id: root

    property string icon_: ""
    property string toolTip: ""
    property color color: theme.subTextColor
    property color bgColor_: "transparent"
    property color bgHoverColor_: theme.coverColor1
    property color bgPressColor_: theme.coverColor2
    property real radius: size_.btnRadius
    property real margins: Math.max(2, size_.smallSpacing * 0.6)
    readonly property bool hovered: mouseArea.containsMouse
    readonly property bool pressed: mouseArea.pressed
    signal clicked()

    implicitWidth: size_.hTabBarHeight
    implicitHeight: size_.hTabBarHeight

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: root.pressed ? root.bgPressColor_ : (root.hovered ? root.bgHoverColor_ : root.bgColor_)
    }

    Icon_ {
        anchors.fill: parent
        anchors.margins: root.margins
        icon: root.icon_
        color: root.enabled ? root.color : theme.coverColor3
        opacity: root.enabled ? 1 : 0.65
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        enabled: root.enabled
        onClicked: root.clicked()
    }

    ToolTip_ {
        visible: root.hovered && root.toolTip.length > 0
        text: root.toolTip
    }
}
