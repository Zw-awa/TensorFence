import QtQuick 2.15

Item {
    property real scale: 1

    property int line: 16 * scale
    property int smallLine: 13 * scale
    property int largeLine: 20 * scale

    property real textScale: 1
    property int text: line * textScale
    property int smallText: smallLine * textScale
    property int largeText: largeLine * textScale

    property real windowRadius: 0
    property real baseRadius: 6 * scale
    property real btnRadius: baseRadius
    property real panelRadius: baseRadius * 1.7

    property real hTabBarHeight: line * 1.8

    property real spacing: 7 * scale
    property real smallSpacing: 4 * scale

    property string languageScale: qsTr("1.0")

    Component.onCompleted: {
        const s = parseFloat(languageScale)
        if (!isNaN(s)) {
            textScale = s
        }
    }
}
