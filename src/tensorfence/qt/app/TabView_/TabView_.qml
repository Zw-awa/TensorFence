import QtQuick 2.15

import "../TabBar_"

Item {
    anchors.fill: parent

    Rectangle {
        id: tabBand
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: size_.hTabBarHeight
        color: theme.tabBarColor
        clip: true

        HTabBar {
            anchors.fill: parent
        }
    }

    Item {
        id: pageHost
        anchors.top: tabBand.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom

        Component.onCompleted: {
            qmlapp.tab.page.pagesNest.parent = pageHost
        }
    }
}
