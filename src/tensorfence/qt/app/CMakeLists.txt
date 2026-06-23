qt_add_executable(tensorfence_qt
    main.cpp
    appcontroller.cpp
    appcontroller.h
)

qt_add_qml_module(tensorfence_qt
    URI TensorFence.UI
    VERSION 1.0
    QML_FILES
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
        Widgets/MarkdownView.qml
        Widgets/MouseAreaBackgroud.qml
        Widgets/Panel.qml
        Widgets/Text_.qml
        Widgets/TextEdit_.qml
        Widgets/ToolTip_.qml
        Widgets/ToastMessage.qml
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
