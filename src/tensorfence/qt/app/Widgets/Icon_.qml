import QtQuick 2.15
import QtQuick.Effects

Item {
    id: root

    property string icon: ""
    property color color: theme.subTextColor
    property bool mirror: false
    readonly property string iconName: icon === "no" ? "close" : icon
    readonly property url iconSource: iconName.length > 0
        ? Qt.resolvedUrl("../images/icons/" + iconName + ".svg")
        : ""

    transform: Scale {
        origin.x: root.width / 2
        origin.y: root.height / 2
        xScale: root.mirror ? -1 : 1
    }

    Image {
        id: sourceImage
        anchors.fill: parent
        source: root.iconSource
        fillMode: Image.PreserveAspectFit
        smooth: true
        sourceSize.width: Math.max(1, Math.round(width))
        sourceSize.height: Math.max(1, Math.round(height))
        visible: false
    }

    MultiEffect {
        anchors.fill: parent
        source: sourceImage
        colorization: 1.0
        colorizationColor: root.color
        visible: sourceImage.status === Image.Ready
    }
}
