import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

import "../Widgets"

TabPage {
    id: naviPage

    ListModel {
        id: pageModel
    }

    property string introText: ""
    property string welcomeText: `# ` + qsTr("欢迎使用 TensorFence") + `

## 👈 ` + qsTr("请选择工作入口") + `

` + qsTr("你现在可以用它做什么") + `

- ` + qsTr("先把输入、预处理、decode、NMS、量化语义写进契约文件") + `
- ` + qsTr("再把原框架、ONNX、RKNN 放到同一条诊断链路里对照") + `
- ` + qsTr("最终输出“哪一层开始漂”的结论，而不是只看最终框") + `

` + qsTr("建议顺序") + `

1. ` + qsTr("先补契约文件") + `
2. ` + qsTr("再做静态校验") + `
3. ` + qsTr("然后准备阶段对比输入与报告产物") + `

` + qsTr("核心目标") + `   •   ` + qsTr("把 YOLO / PP -> ONNX -> RKNN 这一条链路中的不对齐点找出来") + `
`

    Component.onCompleted: initData()

    function initData() {
        introText = welcomeText
        pageModel.clear()
        const f = qmlapp.tab.infoList
        for (let i = 1, c = f.length; i < c; i++) {
            pageModel.append({
                "title": f[i].title,
                "intro": f[i].intro,
                "infoIndex": i,
            })
        }
    }

    DoubleRowLayout {
        anchors.fill: parent
        initSplitterX: size_.line * 15

        leftItem: Panel {
            anchors.fill: parent

            Item {
                id: topLable
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: size_.spacing
                height: size_.line * 2.5

                Text_ {
                    anchors.centerIn: parent
                    text: qsTr("工作入口")
                    color: theme.subTextColor
                }

                MouseAreaBackgroud {
                    onHoveredChanged: naviPage.introText = naviPage.welcomeText
                }
            }

            ScrollView {
                id: scrollView
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.top: topLable.bottom
                anchors.margins: size_.spacing
                clip: true

                Column {
                    width: scrollView.availableWidth
                    spacing: size_.spacing * 0.5

                    Repeater {
                        model: pageModel

                        Button_ {
                            required property string title
                            required property string intro
                            required property int infoIndex

                            text_: title
                            width: scrollView.availableWidth
                            height: size_.line * 2.5

                            onHoveredChanged: {
                                naviPage.introText = intro
                            }
                            onClicked: {
                                const i = qmlapp.tab.getTabPageIndex(naviPage)
                                if (i >= 0) {
                                    qmlapp.tab.changeTabPage(i, infoIndex)
                                }
                            }
                        }
                    }
                }
            }
        }

        rightItem: Panel {
            anchors.fill: parent

            MarkdownView {
                id: introView
                anchors.fill: parent
                anchors.margins: size_.spacing * 2
                text: introText
            }
        }
    }
}
