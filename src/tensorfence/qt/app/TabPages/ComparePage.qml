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
                anchors.top: parent.top
                anchors.margins: size_.spacing
                spacing: size_.spacing * 0.5

                Button_ {
                    text_: qsTr("载入输入")
                    width: parent.width
                    height: size_.line * 2.5
                    onHoveredChanged: if (hovered) page.introText = qsTr("# 载入输入\n\n选择 ONNX、RKNN、框架输出文件，以及阶段对比需要的产物。\n\n文件准备得越规范，后面的诊断越直接。")
                    onClicked: qmlapp.pickInputFile()
                }

                Button_ {
                    text_: qsTr("运行对比")
                    width: parent.width
                    height: size_.line * 2.5
                    onHoveredChanged: if (hovered) page.introText = qsTr("# 运行对比\n\n按照契约统一 preprocess / decode / NMS 语义后，执行阶段比较。\n\n目标不是只跑通，而是找出第一处不一致。")
                    onClicked: qmlapp.acknowledge(qsTr("运行对比"))
                }

                Button_ {
                    text_: qsTr("查看结论")
                    width: parent.width
                    height: size_.line * 2.5
                    onHoveredChanged: if (hovered) page.introText = qsTr("# 查看结论\n\n先看漂移起点，再回头看最终框和最终掩码。\n\n真正有价值的是定位，不是只知道结果错了。")
                    onClicked: qmlapp.acknowledge(qsTr("查看结论"))
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
