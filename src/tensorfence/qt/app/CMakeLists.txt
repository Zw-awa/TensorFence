qt_add_executable(tensorfence_qt
    main.cpp
)

target_link_libraries(tensorfence_qt PRIVATE Qt6::Widgets)

set_target_properties(tensorfence_qt PROPERTIES
    WIN32_EXECUTABLE ON
    MACOSX_BUNDLE ON
)

