import QtQuick 2.15

Item {
    property var infoList: [
        {
            key: "home",
            url: "HomePage.qml",
            title: qsTr("开始使用"),
            intro: qsTr("# 开始使用\n\n把契约、模型、图像和对比产物组织到同一条排查链路里。")
        },
        {
            key: "contracts",
            url: "ContractsPage.qml",
            title: qsTr("契约文件"),
            intro: qsTr("# 契约文件\n\n强制把输入、预处理、decode、NMS、量化这些语义写清楚。\n\n避免“模型能跑，但行为已经不对齐”。")
        },
        {
            key: "reports",
            url: "ReportsPage.qml",
            title: qsTr("诊断报告"),
            intro: qsTr("# 诊断报告\n\n集中查看 `report.json`、`report.md`、`tensor_diffs.json` 这类产物。\n\n重点不是只看最终框，而是看哪一层开始漂。")
        },
        {
            key: "compare",
            url: "ComparePage.qml",
            title: qsTr("阶段对比"),
            intro: qsTr("# 阶段对比\n\n对比 `原框架 -> ONNX -> RKNN` 三段输出。\n\n目标是把问题定位到中间张量，而不是只在最终结果上猜。")
        },
        {
            key: "settings",
            url: "SettingsPage.qml",
            title: qsTr("工程环境"),
            intro: qsTr("# 工程环境\n\n管理 Qt 前端、Python/Conda 环境、WSL/RKNN 工作流入口。")
        }
    ]

    property var pageList: []

    function initListUrl() {
        for (let i = infoList.length - 1; i >= 0; i--) {
            const info = infoList[i]
            if (!info.url) {
                info.url = `${info.key}.qml`
            }
        }
    }

    function getComp(infoIndex) {
        const info = infoList[infoIndex]
        if (info.comp) {
            return info.comp
        }
        const comp = Qt.createComponent(info.url)
        if (comp.status === Component.Ready) {
            infoList[infoIndex].comp = comp
            return comp
        }
        console.error(`Failed to load page component: ${info.url}`)
        return undefined
    }

    function newPage(infoIndex) {
        const info = infoList[infoIndex]
        const comp = getComp(infoIndex)
        if (!comp) {
            return undefined
        }
        const obj = comp.createObject(pagesNest, {
            z: -1,
            visible: false,
            pageKey: info.key
        })
        return {
            obj: obj,
            info: info,
            infoIndex: infoIndex
        }
    }

    function addPage(index, infoIndex) {
        const page = newPage(infoIndex)
        if (page === undefined) {
            return false
        }
        pageList.splice(index, 0, page)
        return true
    }

    function changePage(index, infoIndex) {
        const page = pageList[index]
        const nextPage = newPage(infoIndex)
        if (nextPage === undefined) {
            return false
        }
        page.obj.destroy()
        pageList[index] = nextPage
        return true
    }

    function delPage(index) {
        const page = pageList[index]
        page.obj.destroy()
        pageList.splice(index, 1)
        return true
    }

    function showPage(index) {
        for (let i = 0; i < pageList.length; i++) {
            if (i === index) {
                pageList[i].obj.z = 0
                pageList[i].obj.visible = true
                pageList[i].obj.showPage()
            } else {
                pageList[i].obj.z = -1
                pageList[i].obj.visible = false
            }
        }
    }

    function movePage(index, go) {
        const page = pageList.splice(index, 1)[0]
        pageList.splice(go, 0, page)
    }

    Item {
        id: pagesNest
        anchors.fill: parent
    }

    property var pagesNest: pagesNest
}
