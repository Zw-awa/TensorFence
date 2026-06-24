import QtQuick 2.15

Repeater {
    id: root

    model: ListModel { }

    Component.onCompleted: {
        qmlapp.tab.bar = root
    }

    function addTab(index, title) {
        const insertAt = index < 0 ? model.count : Math.min(index, model.count)
        model.insert(insertAt, { "title_": title, "checked_": false })
    }

    function clearTabs() {
        model.clear()
    }

    function delTab(index) {
        if (!isIndex(index)) {
            return
        }
        model.remove(index)
    }

    function changeTab(index, title) {
        if (!isIndex(index)) {
            return
        }
        model.set(index, { "title_": title, "checked_": false })
        showTab(index)
    }

    function showTab(index) {
        if (!isIndex(index)) {
            return
        }
        for (let i = 0; i < model.count; i++) {
            itemAt(i).checked = i === index
        }
    }

    function moveTab(index, go) {
        if (!isIndex(index) || !isIndex(go) || index === go) {
            return
        }
        model.move(index, go, 1)
        resetIndex()
    }

    function resetIndex() {
        for (let i = 0; i < model.count; i++) {
            const item = itemAt(i)
            if (item) {
                item.pageIndex = i
            }
        }
    }

    function isIndex(index) {
        return index >= 0 && index < model.count
    }

    onItemAdded: resetIndex()
    onItemRemoved: resetIndex()
}
