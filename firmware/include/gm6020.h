#pragma once
#include <stdint.h>
#include "stm32f4xx_hal.h"

typedef struct {
    uint16_t raw_angle;
    int16_t rpm;
    int16_t torque_current;
    uint8_t temperature;
    int32_t turns;
    int32_t total_counts;
    uint16_t last_raw_angle;
    uint8_t initialized;
} gm6020_feedback_t;

void gm6020_feedback_init(gm6020_feedback_t *fb);
void gm6020_parse_feedback(gm6020_feedback_t *fb, const uint8_t data[8]);
float gm6020_angle_deg(const gm6020_feedback_t *fb);
HAL_StatusTypeDef gm6020_send_current(CAN_HandleTypeDef *hcan, int16_t current_cmd);
