import QtQuick 2.15
import QtQuick.Controls 2.15

import "../Widgets"

TabPage {
    id: page

    property string introText: qsTr("# 契约文件\n\n这里先把输入、预处理、decode、NMS、量化这些约束写清楚。\n\n先对齐语义，再谈执行。\n\n如果字段含义没钉死，后面的 ONNX / RKNN 对比基本一定会失真。")

    DoubleRowLayout {
        anchors.fill: parent
        initSplitterX: size_.line * 15

        leftItem: Panel {
            anchors.fill: parent

            Item {
                id: leftHeader
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: size_.spacing
                height: size_.line * 2.5

                Text_ {
                    anchors.centerIn: parent
                    text: qsTr("契约操作")
                    color: theme.subTextColor
                }
            }

            Column {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.topMargin: size_.spacing
                anchors.top: leftHeader.bottom
                anchors.margins: size_.spacing
                spacing: size_.spacing * 0.5

                Button_ {
                    text_: qsTr("载入契约")
                    width: parent.width
                    height: size_.line * 2.5
                    onHoveredChanged: if (hovered) page.introText = qsTr("# 载入契约\n\n载入 YAML 契约文件，查看输入输出语义。\n\n适合先核对 layout、shape、颜色通道、输入范围。")
                    onClicked: qmlapp.pickFile("contract")
                }

                Button_ {
                    text_: qsTr("静态校验")
                    width: parent.width
                    height: size_.line * 2.5
                    onHoveredChanged: if (hovered) page.introText = qsTr("# 静态校验\n\n尽早发现 layout、shape、字段缺失、输入输出未对齐之类的问题。\n\n这一步越早做，后面浪费的时间越少。")
                    enabled: !appController.commandRunning
                    onClicked: appController.runContractValidation()
                }

                Button_ {
                    text_: qsTr("生成草稿")
                    width: parent.width
                    height: size_.line * 2.5
                    onHoveredChanged: if (hovered) page.introText = qsTr("# 生成草稿\n\n先生成可填写的契约骨架，再逐项补全。\n\n适合第一次接一个新模型时快速落地。")
                    onClicked: qmlapp.triggerWorkflow("draft")
                }
            }
        }

        rightItem: Panel {
            anchors.fill: parent

            Column {
                anchors.fill: parent
                anchors.margins: size_.spacing * 2
                spacing: size_.spacing

                LoadedFilesSummary {
                    width: parent.width
                    entries: [
                        { label: qsTr("契约"), path: appController.contractPath }
                    ]
                }

                MarkdownView {
                    width: parent.width
                    height: Math.max(0, parent.height - y)
                    text: appController.commandOutput.length > 0 ? "# 命令输出\n\n```text\n" + appController.commandOutput + "\n```" : page.introText
                }
            }
        }
    }
}
