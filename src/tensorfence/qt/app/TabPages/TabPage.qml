import QtQuick 2.15

Item {
    anchors.fill: parent

    property string pageKey: ""
    signal showPage

    function closePage() {
        delPage()
    }

    function delPage() {
        const index = qmlapp.tab.getTabPageIndex(this)
        qmlapp.tab.delTabPage(index)
    }
}
