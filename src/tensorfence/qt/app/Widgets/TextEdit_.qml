import QtQuick 2.15
import QtQuick.Controls 2.15

TextEdit {
    wrapMode: TextEdit.Wrap
    selectByMouse: true
    selectByKeyboard: true
    color: theme.textColor
    selectedTextColor: theme.bgColor
    selectionColor: theme.specialTextColor
    font.pixelSize: size_.text
    font.family: theme.dataFontFamily
}
