set(TENSORFENCE_APP_SOURCES
    main.cpp
    appcontroller.cpp
    appcontroller.h
)

set(TENSORFENCE_QML_FILES
    Main.qml
    MainWindow/Size_.qml
    Themes/Theme.qml
    TabBar_/BarManager.qml
    TabBar_/HTabBar.qml
    TabBar_/TabButton_.qml
    TabView_/TabView_.qml
    TabView_/TabViewManager.qml
    TabPages/PagesManager.qml
    TabPages/TabPage.qml
    TabPages/HomePage.qml
    TabPages/ContractsPage.qml
    TabPages/ReportsPage.qml
    TabPages/ComparePage.qml
    TabPages/SettingsPage.qml
    Widgets/Button_.qml
    Widgets/DoubleRowLayout.qml
    Widgets/Icon_.qml
    Widgets/IconButton.qml
    Widgets/LoadedFilesSummary.qml
    Widgets/MarkdownView.qml
    Widgets/MouseAreaBackgroud.qml
    Widgets/Panel.qml
    Widgets/Text_.qml
    Widgets/TextEdit_.qml
    Widgets/ToolTip_.qml
    Widgets/ToastMessage.qml
)

set(TENSORFENCE_QML_RESOURCES
    images/icons/add.svg
    images/icons/arrow_to_center.svg
    images/icons/arrow_to_left.svg
    images/icons/close.svg
    images/icons/folder.svg
    images/icons/lock.svg
    images/icons/lock_open.svg
    images/icons/menu.svg
    images/icons/pin.svg
    images/icons/run.svg
    images/icons/save.svg
    images/icons/split_view.svg
)

qt_agent_add_qml_executable(tensorfence_qt
    URI TensorFence.UI
    VERSION 1.0
    RESOURCE_PREFIX "/TensorFence/UI"
    RESOURCE_BASE "${CMAKE_CURRENT_SOURCE_DIR}"
    SOURCES ${TENSORFENCE_APP_SOURCES}
    MOC_HEADERS appcontroller.h
    QML_FILES ${TENSORFENCE_QML_FILES}
    RESOURCES ${TENSORFENCE_QML_RESOURCES}
)
target_link_libraries(tensorfence_qt PRIVATE
    Qt6::Core
    Qt6::Quick
    Qt6::Qml
    Qt6::QuickControls2
    Qt6::QuickDialogs2
)

set_target_properties(tensorfence_qt PROPERTIES
    WIN32_EXECUTABLE ON
    MACOSX_BUNDLE ON
)
