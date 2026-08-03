cmake_minimum_required(VERSION 3.24)

project(TensorFence VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")

find_package(Qt6 6.5 REQUIRED COMPONENTS Core Quick Qml QuickControls2 QuickDialogs2)
qt_standard_project_setup()

set(_qt_agent_safe_default OFF)
if(DEFINED ENV{CODEX_THREAD_ID})
    set(_qt_agent_safe_default ON)
endif()
option(
    QT_AGENT_SAFE_BUILD
    "Avoid CMake autogen subprocesses in restricted agent environments"
    ${_qt_agent_safe_default}
)

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")
include(QtAgentSafe)

add_subdirectory(src/tensorfence/qt)
