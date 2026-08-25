import QtQuick 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property string message: ""
    property string tone: "info"

    visible: opacity > 0
    opacity: 0
    radius: size_.panelRadius
    color: theme.bgColor
    border.width: 1
    border.color: tone === "warning" ? theme.noColor : theme.coverColor2
    width: Math.min(360, parent ? parent.width - size_.spacing * 4 : 360)
    height: Math.max(size_.line * 2.6, messageText.implicitHeight + size_.spacing * 2)
    z: 99

    Behavior on opacity {
        NumberAnimation {
            duration: 160
        }
    }

    function showMessage(msg, msgTone) {
        message = msg
        tone = msgTone || "info"
        opacity = 1
        hideTimer.restart()
    }

    Timer {
        id: hideTimer
        interval: 3200
        onTriggered: root.opacity = 0
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: size_.spacing
        spacing: size_.smallSpacing

        Rectangle {
            width: size_.line * 0.5
            height: width
            radius: width / 2
            color: root.tone === "warning" ? theme.noColor : theme.specialTextColor
        }

        Text_ {
            id: messageText
            text: root.message
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            maximumLineCount: 2
        }
    }
}
