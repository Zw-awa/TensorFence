import QtQuick 2.15

import "../TabPages"

Item {
    id: tabViewManager

    PagesManager {
        id: page
    }

    property alias page: page
    property var bar: undefined
    property alias infoList: page.infoList
    property alias pageList: page.pageList
    property bool barIsLock: false
    property int showPageIndex: -1

    function init() {
        page.initListUrl()
        if (pageList.length === 0) {
            addNavi()
        } else {
            showTabPage(0)
        }
    }

    function addTabPage(index, infoIndex) {
        if (index < 0) {
            index = pageList.length
        }
        if (!page.addPage(index, infoIndex)) {
            return -1
        }
        if (bar) {
            bar.addTab(index, infoList[infoIndex].title)
        }
        if (showPageIndex >= index) {
            showPageIndex++
        }
        return index
    }

    function addNavi() {
        const index = addTabPage(-1, 0)
        if (index >= 0) {
            showTabPage(index)
        }
    }

    function closeTabPage(index) {
        delTabPage(index)
    }

    function delTabPage(index) {
        if (!isIndex(index, pageList)) {
            return
        }
        page.delPage(index)
        if (bar) {
            bar.delTab(index)
        }
        if (showPageIndex > index) {
            showPageIndex--
        } else if (showPageIndex === index) {
            if (pageList.length === 0) {
                addNavi()
                return
            }
            showTabPage(Math.min(index, pageList.length - 1))
            return
        }
    }

    function changeTabPage(index, infoIndex) {
        if (!isIndex(index, pageList)) {
            return
        }
        if (!isIndex(infoIndex, infoList)) {
            return
        }
        for (let i = 0; i < pageList.length; i++) {
            if (pageList[i].infoIndex === infoIndex) {
                showTabPage(i)
                return
            }
        }
        if (!page.changePage(index, infoIndex)) {
            return
        }
        if (bar) {
            bar.changeTab(index, infoList[infoIndex].title)
        }
        if (showPageIndex === index) {
            showTabPage(index)
        }
    }

    function showTabPage(index) {
        if (index < 0) {
            index = pageList.length - 1
        }
        if (!isIndex(index, pageList)) {
            return
        }
        showPageIndex = index
        page.showPage(index)
        if (bar) {
            bar.showTab(index)
        }
        if (typeof appController !== "undefined") {
            appController.navigateTo(pageList[index].info.key)
        }
    }

    function showPageKey(key) {
        const infoIndex = findInfoIndexByKey(key)
        if (infoIndex < 0) {
            return
        }
        for (let i = 0; i < pageList.length; i++) {
            if (pageList[i].info.key === key) {
                showTabPage(i)
                return
            }
        }
        if (showPageIndex >= 0 && pageList[showPageIndex].info.key === "home") {
            changeTabPage(showPageIndex, infoIndex)
            showTabPage(showPageIndex)
            return
        }
        const index = addTabPage(-1, infoIndex)
        if (index >= 0) {
            showTabPage(index)
        }
    }

    function moveTabPage(index, go) {
        if (!isIndex(index, pageList) || !isIndex(go, pageList)) {
            return
        }
        page.movePage(index, go)
        if (bar) {
            bar.moveTab(index, go)
        }
        if (showPageIndex === index) {
            showPageIndex = go
        }
    }

    function getTabPageIndex(obj) {
        for (let i = 0; i < pageList.length; i++) {
            if (pageList[i].obj === obj) {
                return i
            }
        }
        return -1
    }

    function findInfoIndexByKey(key) {
        for (let i = 0; i < infoList.length; i++) {
            if (infoList[i].key === key) {
                return i
            }
        }
        return -1
    }

    function isIndex(index, list) {
        return index >= 0 && index < list.length
    }
}
