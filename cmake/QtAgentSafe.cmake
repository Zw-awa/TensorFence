include(CMakeParseArguments)

function(qt_agent_add_qml_executable target)
    set(options)
    set(oneValueArgs URI VERSION RESOURCE_PREFIX RESOURCE_BASE)
    set(multiValueArgs SOURCES MOC_HEADERS QML_FILES RESOURCES)
    cmake_parse_arguments(QT_APP "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

    if(NOT QT_APP_URI)
        message(FATAL_ERROR "qt_agent_add_qml_executable requires URI")
    endif()
    if(NOT QT_APP_VERSION)
        set(QT_APP_VERSION 1.0)
    endif()

    if(QT_AGENT_SAFE_BUILD)
        set(CMAKE_AUTOMOC OFF)
        qt_wrap_cpp(_qt_agent_moc_sources ${QT_APP_MOC_HEADERS})
        qt_add_executable(${target}
            ${QT_APP_SOURCES}
            ${_qt_agent_moc_sources}
        )
        qt_add_resources(${target} "${target}_qml"
            PREFIX "${QT_APP_RESOURCE_PREFIX}"
            BASE "${QT_APP_RESOURCE_BASE}"
            FILES
                ${QT_APP_QML_FILES}
                ${QT_APP_RESOURCES}
        )
    else()
        qt_add_executable(${target} ${QT_APP_SOURCES})
        qt_add_qml_module(${target}
            URI ${QT_APP_URI}
            VERSION ${QT_APP_VERSION}
            QML_FILES ${QT_APP_QML_FILES}
            RESOURCES ${QT_APP_RESOURCES}
        )
    endif()
endfunction()
