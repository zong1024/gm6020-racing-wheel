#include "wheel_app.h"
#include "app_config.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

static float clampf(float x, float lo, float hi) {
    return x < lo ? lo : (x > hi ? hi : x);
}

static void uart_send(wheel_app_t *app, const char *msg) {
    HAL_UART_Transmit(app->huart, (uint8_t *)msg, (uint16_t)strlen(msg), 10);
}

void wheel_app_init(wheel_app_t *app, CAN_HandleTypeDef *hcan, UART_HandleTypeDef *huart) {
    memset(app, 0, sizeof(*app));
    app->hcan = hcan;
    app->huart = huart;
    gm6020_feedback_init(&app->motor);
    pid_init(&app->position_pid, 120.0f, 0.0f, 2.5f, -CURRENT_CMD_LIMIT, CURRENT_CMD_LIMIT);
    app->state = WHEEL_CENTERING;
}

void wheel_app_start(wheel_app_t *app) {
    app->centering_start_ms = HAL_GetTick();
    app->last_control_ms = app->centering_start_ms;
    HAL_UART_Receive_IT(app->huart, &app->uart_byte, 1);
    uart_send(app, "STATE,CENTERING\r\n");
}

void wheel_app_request_center(wheel_app_t *app) {
    app->state = WHEEL_CENTERING;
    app->centering_start_ms = HAL_GetTick();
    pid_reset(&app->position_pid);
    uart_send(app, "STATE,CENTERING\r\n");
}

void wheel_app_on_can_rx(wheel_app_t *app, const CAN_RxHeaderTypeDef *hdr, const uint8_t data[8]) {
    if (hdr->IDE == CAN_ID_STD && hdr->StdId == (GM6020_CAN_RX_ID_BASE + GM6020_MOTOR_INDEX)) {
        gm6020_parse_feedback(&app->motor, data);
        app->measured_deg = gm6020_angle_deg(&app->motor);
        app->relative_deg = app->measured_deg - app->zero_deg;
        app->last_feedback_ms = HAL_GetTick();
    }
}

static void handle_line(wheel_app_t *app, char *line) {
    if (strncmp(line, "A,", 2) == 0) {
        app->target_deg = clampf(strtof(line + 2, NULL), -WHEEL_SOFT_LIMIT_DEG, WHEEL_SOFT_LIMIT_DEG);
    } else if (strncmp(line, "PID,", 4) == 0) {
        float kp, ki, kd;
        if (sscanf(line + 4, "%f,%f,%f", &kp, &ki, &kd) == 3) {
            app->position_pid.kp = kp;
            app->position_pid.ki = ki;
            app->position_pid.kd = kd;
            pid_reset(&app->position_pid);
        }
    } else if (strcmp(line, "CENTER") == 0) {
        wheel_app_request_center(app);
    }
}

void wheel_app_on_uart_byte(wheel_app_t *app, uint8_t byte) {
    if (byte == '\n' || byte == '\r') {
        if (app->uart_rx_len > 0) {
            app->uart_rx[app->uart_rx_len] = '\0';
            handle_line(app, app->uart_rx);
            app->uart_rx_len = 0;
        }
    } else if (app->uart_rx_len < UART_RX_FRAME_MAX - 1) {
        app->uart_rx[app->uart_rx_len++] = (char)byte;
    } else {
        app->uart_rx_len = 0;
    }
}

void wheel_app_tick(wheel_app_t *app, uint32_t now_ms) {
    if ((now_ms - app->last_control_ms) < CONTROL_PERIOD_MS) {
        return;
    }

    float dt_s = (float)(now_ms - app->last_control_ms) / 1000.0f;
    app->last_control_ms = now_ms;

    if (!app->motor.initialized || (now_ms - app->last_feedback_ms) > 100U) {
        app->state = WHEEL_FAULT;
        gm6020_send_current(app->hcan, 0);
        return;
    }

    if (app->state == WHEEL_CENTERING) {
        gm6020_send_current(app->hcan, 0);
        if ((now_ms - app->centering_start_ms) >= CENTER_SETTLE_MS &&
            abs(app->motor.rpm) <= CENTER_VELOCITY_EPS_RPM) {
            app->zero_deg = app->measured_deg;
            app->relative_deg = 0.0f;
            app->target_deg = 0.0f;
            app->state = WHEEL_READY;
            pid_reset(&app->position_pid);
            uart_send(app, "STATE,READY\r\n");
        }
        return;
    }

    if (app->state == WHEEL_READY) {
        float safe_target = clampf(app->target_deg, -WHEEL_SOFT_LIMIT_DEG, WHEEL_SOFT_LIMIT_DEG);
        if (app->relative_deg <= -WHEEL_SOFT_LIMIT_DEG && safe_target < app->relative_deg) {
            safe_target = app->relative_deg;
        }
        if (app->relative_deg >= WHEEL_SOFT_LIMIT_DEG && safe_target > app->relative_deg) {
            safe_target = app->relative_deg;
        }
        int16_t current_cmd = (int16_t)pid_update(&app->position_pid, safe_target, app->relative_deg, dt_s);
        gm6020_send_current(app->hcan, current_cmd);

        char telemetry[96];
        int n = snprintf(telemetry, sizeof telemetry, "T,%.2f,%.2f,%d,%d\r\n",
                         app->relative_deg, safe_target, app->motor.rpm, app->motor.torque_current);
        HAL_UART_Transmit(app->huart, (uint8_t *)telemetry, (uint16_t)n, 2);
    }
}
