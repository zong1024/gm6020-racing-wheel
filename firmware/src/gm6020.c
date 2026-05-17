#include "gm6020.h"
#include "app_config.h"

void gm6020_feedback_init(gm6020_feedback_t *fb) {
    *fb = (gm6020_feedback_t){0};
}

void gm6020_parse_feedback(gm6020_feedback_t *fb, const uint8_t data[8]) {
    uint16_t raw = ((uint16_t)data[0] << 8) | data[1];
    fb->rpm = (int16_t)(((uint16_t)data[2] << 8) | data[3]);
    fb->torque_current = (int16_t)(((uint16_t)data[4] << 8) | data[5]);
    fb->temperature = data[6];

    if (fb->initialized) {
        int32_t delta = (int32_t)raw - (int32_t)fb->last_raw_angle;
        if (delta > 4096) {
            fb->turns--;
        } else if (delta < -4096) {
            fb->turns++;
        }
    } else {
        fb->initialized = 1;
    }

    fb->raw_angle = raw;
    fb->last_raw_angle = raw;
    fb->total_counts = fb->turns * (int32_t)GM6020_ENCODER_CPR + raw;
}

float gm6020_angle_deg(const gm6020_feedback_t *fb) {
    return ((float)fb->total_counts * 360.0f) / GM6020_ENCODER_CPR;
}

HAL_StatusTypeDef gm6020_send_current(CAN_HandleTypeDef *hcan, int16_t current_cmd) {
    CAN_TxHeaderTypeDef tx = {0};
    uint8_t data[8] = {0};
    uint32_t mailbox;
    tx.StdId = GM6020_CAN_TX_ID;
    tx.IDE = CAN_ID_STD;
    tx.RTR = CAN_RTR_DATA;
    tx.DLC = 8;
    data[0] = (uint8_t)((current_cmd >> 8) & 0xFF);
    data[1] = (uint8_t)(current_cmd & 0xFF);
    return HAL_CAN_AddTxMessage(hcan, &tx, data, &mailbox);
}
