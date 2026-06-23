import QtQuick 2.15
import QtQuick.Controls 2.15

ToolTip {
    id: root

    delay: 350
    timeout: 0
    y: size_.line

    contentItem: Text {
        text: root.text
        font.family: theme.fontFamily
        font.pixelSize: size_.smallText
        color: theme.textColor
    }

    background: Rectangle {
        color: theme.bgColor
        border.width: 1
        border.color: theme.coverColor3
        radius: size_.btnRadius
    }
}
