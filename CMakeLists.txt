cmake_minimum_required(VERSION 3.24)

project(TensorFence VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")

find_package(Qt6 6.5 REQUIRED COMPONENTS Core Quick Qml QuickControls2 QuickDialogs2)
qt_standard_project_setup()

add_subdirectory(src/tensorfence/qt)
