import QtQuick 2.15

Item {
    id: root

    property var entries: []
    property string emptyText: qsTr("尚未载入文件")
    implicitHeight: content.implicitHeight

    Column {
        id: content
        width: parent.width
        spacing: size_.smallSpacing

        Text_ {
            width: parent.width
            text: qsTr("当前加载")
            color: theme.subTextColor
            font.bold: true
        }

        Repeater {
            model: root.entries

            delegate: Item {
                required property var modelData
                width: content.width
                height: loadedPath.implicitHeight + size_.smallSpacing

                Text_ {
                    id: loadedPath
                    width: parent.width
                    text: modelData.path.length > 0
                        ? modelData.label + qsTr("：") + modelData.path.split(/[\\/]/).pop() + "\n" + modelData.path
                        : modelData.label + qsTr("：未选择")
                    color: modelData.path.length > 0 ? theme.textColor : theme.subTextColor
                    wrapMode: Text.Wrap
                }
            }
        }

        Text_ {
            visible: root.entries.length === 0
            width: parent.width
            text: root.emptyText
            color: theme.subTextColor
        }
    }
}
