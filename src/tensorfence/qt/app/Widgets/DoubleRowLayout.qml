import QtQuick 2.15

Item {
    id: root

    property QtObject leftItem
    property QtObject rightItem
    property real hideWidth: 96
    property real initSplitterX: 0.34
    property string saveKey: ""
    property real margins: size_.spacing
    property bool isShowSplitView: false
    property int hideLR: 0
    signal switchView()

    property real handleWidth: Math.max(10, size_.spacing)
    property real splitterX: 0

    function innerWidth() {
        return width - margins * 2
    }

    function resetSplitter() {
        if (initSplitterX > 0 && initSplitterX < 1) {
            splitterX = innerWidth() * initSplitterX - handleWidth * 0.5
        } else if (initSplitterX >= 1) {
            splitterX = initSplitterX
        } else {
            splitterX = innerWidth() * 0.34
        }
        clampSplitter()
    }

    function clampSplitter() {
        const minX = hideWidth
        const maxX = innerWidth() - hideWidth - handleWidth
        splitterX = Math.max(0, Math.min(splitterX, innerWidth() - handleWidth))
        if (hideLR === 0) {
            splitterX = Math.max(minX, Math.min(splitterX, maxX))
        } else if (hideLR === 1) {
            splitterX = 0
        } else if (hideLR === 2) {
            splitterX = innerWidth() - handleWidth
        }
    }

    function showBoth() {
        hideLR = 0
        clampSplitter()
    }

    function showRightOnly() {
        hideLR = 1
        clampSplitter()
    }

    function showLeftOnly() {
        hideLR = 2
        clampSplitter()
    }

    onWidthChanged: {
        if (splitterX === 0) {
            resetSplitter()
        } else {
            clampSplitter()
        }
    }

    Component.onCompleted: resetSplitter()

    onLeftItemChanged: if (leftItem) leftItem.parent = leftHost
    onRightItemChanged: if (rightItem) rightItem.parent = rightHost

    Item {
        id: contentRoot
        anchors.fill: parent
        anchors.margins: root.margins

        Item {
            id: leftHost
            x: 0
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: root.hideLR === 1 ? 0 : divider.x
            visible: root.hideLR !== 1
        }

        Item {
            id: rightHost
            x: divider.x + divider.width
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: root.hideLR === 2 ? 0 : Math.max(0, contentRoot.width - x)
            visible: root.hideLR !== 2
        }

        Item {
            id: divider
            x: root.splitterX
            width: root.handleWidth
            anchors.top: parent.top
            anchors.bottom: parent.bottom

            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: Math.max(2, parent.width * 0.24)
                radius: width * 0.5
                color: splitterMouseArea.pressed ? theme.coverColor4 : (splitterMouseArea.containsMouse ? theme.coverColor3 : theme.coverColor2)
            }

            MouseArea {
                id: splitterMouseArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: root.hideLR === 0 ? Qt.SizeHorCursor : Qt.PointingHandCursor
                drag.target: root.hideLR === 0 ? divider : undefined
                drag.axis: Drag.XAxis
                drag.minimumX: 0
                drag.maximumX: contentRoot.width - divider.width

                onPositionChanged: {
                    if (drag.active) {
                        root.splitterX = divider.x
                        root.clampSplitter()
                    }
                }
                onReleased: root.clampSplitter()
            }

            Column {
                id: controlsColumn
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                anchors.bottomMargin: size_.spacing
                spacing: Math.max(3, size_.smallSpacing)
                visible: splitterMouseArea.containsMouse || controlsMouse.containsMouse

                Repeater {
                    model: [
                        { icon: "arrow_to_left", action: "left" },
                        { icon: "arrow_to_left", action: "right", mirror: true },
                        { icon: "arrow_to_center", action: "both" }
                    ]

                    delegate: Rectangle {
                        required property var modelData
                        width: size_.line * 1.6
                        height: size_.line * 1.6
                        radius: size_.btnRadius
                        color: controlMouse.containsMouse ? theme.coverColor2 : theme.specialBgColor

                        Icon_ {
                            anchors.fill: parent
                            anchors.margins: 3
                            icon: modelData.icon
                            mirror: !!modelData.mirror
                            color: theme.specialTextColor
                        }

                        MouseArea {
                            id: controlMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: {
                                if (modelData.action === "left") {
                                    root.showLeftOnly()
                                } else if (modelData.action === "right") {
                                    root.showRightOnly()
                                } else {
                                    root.showBoth()
                                }
                            }
                        }
                    }
                }

                MouseArea {
                    id: controlsMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.NoButton
                }
            }
        }
    }
}
