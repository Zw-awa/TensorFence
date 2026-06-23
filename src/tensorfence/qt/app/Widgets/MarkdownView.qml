import QtQuick 2.15
import QtQuick.Controls 2.15

ScrollView {
    id: root

    property string text: ""

    clip: true
    contentWidth: availableWidth

    TextEdit_ {
        id: body
        width: root.availableWidth
        readOnly: true
        textFormat: TextEdit.MarkdownText
        text: root.text
        onLinkActivated: function(link) {
            Qt.openUrlExternally(link)
        }
    }
}
