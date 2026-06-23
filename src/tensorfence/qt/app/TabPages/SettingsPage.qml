import QtQuick 2.15

import "../Widgets"

TabPage {
    id: page

    property string introText: qsTr("# 工程环境\n\n这里先承担环境与工作流入口的职责。\n\n包括 Qt、Conda、WSL、RKNN、真机测试前的准备。")

    DoubleRowLayout {
        anchors.fill: parent
        initSplitterX: size_.line * 15

        leftItem: Panel {
            anchors.fill: parent

            Item {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: size_.spacing
                height: size_.line * 2.5

                Text_ {
                    anchors.centerIn: parent
                    text: qsTr("环境分组")
                    color: theme.subTextColor
                }
            }

            Column {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.topMargin: size_.spacing
                anchors.top: parent.top
                anchors.margins: size_.spacing
                spacing: size_.spacing * 0.5

                Button_ {
                    text_: qsTr("Qt 界面")
                    width: parent.width
                    height: size_.line * 2.5
                    onHoveredChanged: if (hovered) page.introText = qsTr("# Qt 界面\n\n当前前端采用 `CLI first + Qt UI`。\n\nCLI 负责能力，Qt 负责组织、浏览和反馈。")
                }

                Button_ {
                    text_: qsTr("Python / Conda")
                    width: parent.width
                    height: size_.line * 2.5
                    onHoveredChanged: if (hovered) page.introText = qsTr("# Python / Conda\n\nPython 依赖统一由项目环境管理，不污染主环境。\n\n后续 CLI、对比、报告生成都依赖这里。")
                }

                Button_ {
                    text_: qsTr("WSL / RKNN")
                    width: parent.width
                    height: size_.line * 2.5
                    onHoveredChanged: if (hovered) page.introText = qsTr("# WSL / RKNN\n\nWindows 侧做组织与查看，Linux / WSL 侧负责 RKNN 相关工作流。\n\n真机测试前，先把两边环境链路打通。")
                }

                Button_ {
                    text_: qsTr("真机测试")
                    width: parent.width
                    height: size_.line * 2.5
                    onHoveredChanged: if (hovered) page.introText = qsTr("# 真机测试\n\n把契约、模型、图像、阶段输出准备齐，再上板排查。\n\n前面准备越规范，真机阶段越不容易浪费时间。")
                }
            }
        }

        rightItem: Panel {
            anchors.fill: parent

            MarkdownView {
                anchors.fill: parent
                anchors.margins: size_.spacing * 2
                text: page.introText
            }
        }
    }
}
