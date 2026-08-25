import QtQuick 2.15

import "../Widgets"

TabPage {
    id: page

    property string introText: qsTr("# 阶段对比\n\n对比 `原框架 -> ONNX -> RKNN` 三段输出。\n\n目标是输出一份“哪一层开始漂”的诊断报告。\n\n这里是 TensorFence 最核心的工作入口。")

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
                    text: qsTr("对比操作")
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
                    text_: qsTr("选择 FP16 证据")
                    width: parent.width
                    height: size_.line * 2.5
                    onHoveredChanged: if (hovered) page.introText = qsTr("# 载入输入\n\n选择 ONNX、RKNN、框架输出文件，以及阶段对比需要的产物。\n\n文件准备得越规范，后面的诊断越直接。")
                    onClicked: qmlapp.pickFile("fp16")
                }

                Button_ {
                    text_: qsTr("选择 INT8 证据")
                    width: parent.width
                    height: size_.line * 2.5
                    onHoveredChanged: if (hovered) page.introText = qsTr("# 运行对比\n\n按照契约统一 preprocess / decode / NMS 语义后，执行阶段比较。\n\n目标不是只跑通，而是找出第一处不一致。")
                    onClicked: qmlapp.pickFile("int8")
                }

                Button_ {
                    text_: qsTr("校验证据")
                    width: parent.width
                    height: size_.line * 2.5
                    onHoveredChanged: if (hovered) page.introText = qsTr("# 查看结论\n\n先看漂移起点，再回头看最终框和最终掩码。\n\n真正有价值的是定位，不是只知道结果错了。")
                    enabled: !appController.commandRunning
                    onClicked: appController.runCaptureValidation()
                }

                Button_ {
                    text_: qsTr("选择 ONNX 模型")
                    width: parent.width
                    height: size_.line * 2.5
                    onClicked: qmlapp.pickFile("model")
                }

                Button_ {
                    text_: qsTr("探查输出契约")
                    width: parent.width
                    height: size_.line * 2.5
                    enabled: !appController.commandRunning
                    onClicked: appController.runModelProbe()
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
                        { label: qsTr("契约"), path: appController.contractPath },
                        { label: qsTr("FP16 证据"), path: appController.fp16ArtifactPath },
                        { label: qsTr("INT8 证据"), path: appController.int8ArtifactPath },
                        { label: qsTr("ONNX 模型"), path: appController.modelPath }
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
