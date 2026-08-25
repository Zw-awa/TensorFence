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
                id: leftHeader
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
                anchors.top: leftHeader.bottom
                anchors.margins: size_.spacing
                spacing: size_.spacing * 0.5

                Button_ {
                    text_: qsTr("选择 TensorFence CLI")
                    width: parent.width
                    height: size_.line * 2.5
                    onHoveredChanged: if (hovered) page.introText = qsTr("# TensorFence CLI\n\n选择已安装的 `tensorfence.exe`。它直接执行 TensorFence 命令。\n\n适合已执行过 pip install 的环境。")
                    onClicked: qmlapp.pickFile("cli")
                }

                Button_ {
                    text_: qsTr("Python / Conda")
                    width: parent.width
                    height: size_.line * 2.5
                    onHoveredChanged: if (hovered) page.introText = qsTr("# Python / Conda\n\n选择 Conda 环境中的 `python.exe`。Qt 会通过 `python.exe -m tensorfence` 执行命令。\n\n当前环境建议选择 `F:/miniforge3/envs/tensorfence/python.exe`。")
                    onClicked: qmlapp.pickFile("python")
                }

                Button_ {
                    text_: qsTr("WSL / RKNN")
                    width: parent.width
                    height: size_.line * 2.5
                    onHoveredChanged: if (hovered) page.introText = qsTr("# WSL / RKNN\n\nWindows 侧做组织与查看，Linux / WSL 侧负责 RKNN 相关工作流。\n\n真机测试前，先把两边环境链路打通。")
                    onClicked: appController.notifyUnavailable(qsTr("WSL / RKNN"))
                }

                Button_ {
                    text_: qsTr("真机测试")
                    width: parent.width
                    height: size_.line * 2.5
                    onHoveredChanged: if (hovered) page.introText = qsTr("# 真机测试\n\n把契约、模型、图像、阶段输出准备齐，再上板排查。\n\n前面准备越规范，真机阶段越不容易浪费时间。")
                    onClicked: appController.notifyUnavailable(qsTr("真机测试"))
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
                        { label: qsTr("本机 CLI / Python"), path: appController.cliPath }
                    ]
                }

                MarkdownView {
                    width: parent.width
                    height: Math.max(0, parent.height - y)
                    text: "# 工程环境\n\nQt 将只调用此 Windows 本机可执行文件。WSL/RKNN 负责采集，再导入 artifact 进行诊断。"
                }
            }
        }
    }
}
