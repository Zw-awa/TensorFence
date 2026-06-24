import QtQuick 2.15
import QtQuick.Controls 2.15

ScrollView {
    id: root

    property string text: ""

    clip: true
    contentWidth: availableWidth

    Text_ {
        id: body
        width: root.availableWidth
        height: implicitHeight
        textFormat: Text.MarkdownText
        wrapMode: Text.Wrap
        text: root.text
        lineHeight: 1.35
        lineHeightMode: Text.ProportionalHeight
        onLinkActivated: function(link) {
            Qt.openUrlExternally(link)
        }
    }
}
