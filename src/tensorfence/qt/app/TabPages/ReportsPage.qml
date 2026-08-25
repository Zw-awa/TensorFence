import QtQuick 2.15

import "../Widgets"

TabPage {
    id: page

    property string introText: qsTr("# 诊断报告\n\n把阶段对比产物统一收拢到这里看。\n\n重点看哪一层开始漂、漂了多少，而不是只看最后框差不差。\n\n这里适合做归档、复盘和问题沟通。")

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
                    text: qsTr("报告操作")
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
                    text_: qsTr("载入报告")
                    width: parent.width
                    height: size_.line * 2.5
                    onHoveredChanged: if (hovered) page.introText = qsTr("# 载入报告\n\n载入 `report.json`、`report.md`、`final_summary.json`。\n\n适合快速回看一次阶段对比跑出来的结果。")
                    onClicked: qmlapp.pickFile("report")
                }

                Button_ {
                    text_: qsTr("查看漂移")
                    width: parent.width
                    height: size_.line * 2.5
                    onHoveredChanged: if (hovered) page.introText = qsTr("# 查看漂移\n\n优先关注中间张量差分、统计量和最终结论。\n\n不要先陷在最终框里猜。")
                    onClicked: appController.openReport()
                }

                Button_ {
                    text_: qsTr("导出摘要")
                    width: parent.width
                    height: size_.line * 2.5
                    onHoveredChanged: if (hovered) page.introText = qsTr("# 导出摘要\n\n导出适合沟通和归档的精简报告。\n\n后面可以继续扩成 Markdown / HTML / 结构化 JSON。")
                    onClicked: appController.openReport()
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
                        { label: qsTr("诊断报告"), path: appController.reportPath }
                    ]
                }

                MarkdownView {
                    width: parent.width
                    height: Math.max(0, parent.height - y)
                    text: appController.commandOutput.length > 0 ? "# 最近命令输出\n\n```text\n" + appController.commandOutput + "\n```" : page.introText
                }
            }
        }
    }
}
