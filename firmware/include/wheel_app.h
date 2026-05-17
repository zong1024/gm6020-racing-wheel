#pragma once
#include "stm32f4xx_hal.h"
#include "gm6020.h"
#include "pid.h"

typedef enum {
    WHEEL_CENTERING = 0,
    WHEEL_READY,
    WHEEL_FAULT
} wheel_state_t;

typedef struct {
    CAN_HandleTypeDef *hcan;
    UART_HandleTypeDef *huart;
    gm6020_feedback_t motor;
    pid_t position_pid;
    wheel_state_t state;
    float zero_deg;
    float target_deg;
    float measured_deg;
    float relative_deg;
    uint32_t centering_start_ms;
    uint32_t last_control_ms;
    uint32_t last_feedback_ms;
    char uart_rx[UART_RX_FRAME_MAX];
    uint8_t uart_rx_len;
    uint8_t uart_byte;
} wheel_app_t;

void wheel_app_init(wheel_app_t *app, CAN_HandleTypeDef *hcan, UART_HandleTypeDef *huart);
void wheel_app_start(wheel_app_t *app);
void wheel_app_on_can_rx(wheel_app_t *app, const CAN_RxHeaderTypeDef *hdr, const uint8_t data[8]);
void wheel_app_on_uart_byte(wheel_app_t *app, uint8_t byte);
void wheel_app_tick(wheel_app_t *app, uint32_t now_ms);
void wheel_app_request_center(wheel_app_t *app);
