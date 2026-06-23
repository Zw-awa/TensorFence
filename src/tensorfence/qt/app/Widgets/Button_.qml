import QtQuick 2.15
import QtQuick.Controls 2.15

Button {
    id: root

    property string text_: ""
    property string toolTip: ""
    property bool bold_: false
    property int textSize: size_.text
    property color textColor_: theme.textColor
    property color bgColor_: "transparent"
    property color bgHoverColor_: theme.coverColor1
    property color bgPressColor_: theme.coverColor2
    property int borderWidth: 0
    property color borderColor: theme.coverColor2
    property real radius: size_.btnRadius

    hoverEnabled: true

    contentItem: Text_ {
        text: root.text_
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.pixelSize: root.textSize
        font.bold: root.bold_
        color: root.textColor_
    }

    background: Rectangle {
        radius: root.radius
        color: root.pressed ? root.bgPressColor_ : (root.hovered ? root.bgHoverColor_ : root.bgColor_)
        border.width: root.borderWidth
        border.color: root.borderColor
    }

    ToolTip_ {
        visible: root.hovered && root.toolTip.length > 0
        text: root.toolTip
    }
}
