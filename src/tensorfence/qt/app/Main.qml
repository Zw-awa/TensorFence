import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Dialogs

import "Themes"
import "TabView_"
import "MainWindow"
import "Widgets"

Window {
    id: mainWindowRoot
    visible: true
    visibility: Window.Windowed

    property bool isMainWindowTop: false
    flags: Qt.Window
        | Qt.CustomizeWindowHint
        | Qt.WindowTitleHint
        | Qt.WindowSystemMenuHint
        | Qt.WindowMinMaxButtonsHint
        | Qt.WindowCloseButtonHint
        | (isMainWindowTop ? Qt.WindowStaysOnTopHint : 0)

    width: 800
    height: 500
    minimumWidth: 300
    minimumHeight: 300
    color: "#00000000"
    title: "TensorFence"

    property Theme theme: Theme {}
    property Size_ size_: Size_ {}

    Item {
        id: qmlapp

        TabViewManager {
            id: tab
        }

        QtObject {
            id: globalConfigs
            property var values: ({
                "window.doubleLayout": ({})
            })

            function getValue(key) {
                if (values[key] === undefined) {
                    values[key] = {}
                }
                return values[key]
            }

            function setValue(key, value) {
                values[key] = value
            }
        }

        property alias tab: tab
        property alias globalConfigs: globalConfigs
        property bool enabledEffect: false

        function syncCurrentPage() {
            if (typeof appController !== "undefined") {
                tab.showPageKey(appController.currentPage)
            }
        }

        function openUrls(urls) {
            if (typeof appController === "undefined") {
                return
            }
            appController.handleDroppedUrls(urls)
            syncCurrentPage()
        }

        function openPath(path) {
            if (typeof appController === "undefined") {
                return
            }
            appController.openPath(path)
            syncCurrentPage()
        }

        function triggerWorkflow(workflowId) {
            if (typeof appController === "undefined") {
                return
            }
            appController.activateWorkflow(workflowId)
            syncCurrentPage()
        }

        function pickInputFile() {
            openDialog.open()
        }

        function acknowledge(label) {
            if (typeof appController !== "undefined") {
                appController.acknowledgeAction(label)
            }
        }

        Component.onCompleted: {
            Qt.callLater(function() {
                tab.init()
            })
        }
    }

    FileDialog {
        id: openDialog
        title: qsTr("选择文件")
        fileMode: FileDialog.OpenFile
        nameFilters: [
            qsTr("TensorFence 文件 (*.yaml *.yml *.json *.md *.html *.onnx *.rknn *.npz)"),
            qsTr("所有文件 (*)")
        ]
        onAccepted: {
            qmlapp.openUrls([selectedFile])
        }
    }

    Connections {
        target: typeof appController === "undefined" ? null : appController

        function onBannerRequested(message, tone) {
            toast.showMessage(message, tone)
        }
    }

    Rectangle {
        id: mainContainer
        anchors.fill: parent
        color: "#00000000"
        focus: true

        Keys.enabled: true
        Keys.onEscapePressed: {
            mainWindowRoot.visibility = Window.Minimized
        }

        Rectangle {
            id: mainUI
            anchors.fill: parent
            anchors.margins: 0
            radius: size_.windowRadius
            color: theme.bgColor
            clip: true

            TabView_ {
                anchors.fill: parent
            }

            ToastMessage {
                id: toast
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.rightMargin: size_.spacing * 1.5
                anchors.bottomMargin: size_.spacing * 1.5
            }
        }
    }
}
