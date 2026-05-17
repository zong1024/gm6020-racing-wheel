#pragma once

typedef struct {
    float kp;
    float ki;
    float kd;
    float integrator;
    float prev_error;
    float out_min;
    float out_max;
    float i_min;
    float i_max;
} pid_t;

void pid_init(pid_t *pid, float kp, float ki, float kd, float out_min, float out_max);
void pid_reset(pid_t *pid);
float pid_update(pid_t *pid, float target, float measurement, float dt_s);
