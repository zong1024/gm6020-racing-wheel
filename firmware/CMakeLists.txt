cmake_minimum_required(VERSION 3.20)
project(gm6020_racing_wheel C)

# This CMake file builds the application layer. Point STM32_HAL_ROOT and add your
# CubeMX-generated startup/system files when integrating with the Robomaster C board BSP.
set(APP_SOURCES
    src/main.c
    src/pid.c
    src/gm6020.c
    src/wheel_app.c
)
add_library(wheel_app STATIC ${APP_SOURCES})
target_include_directories(wheel_app PUBLIC include)
target_compile_features(wheel_app PUBLIC c_std_11)
