#include "pid.h"

static float clampf(float x, float lo, float hi) {
    return x < lo ? lo : (x > hi ? hi : x);
}

void pid_init(pid_t *pid, float kp, float ki, float kd, float out_min, float out_max) {
    pid->kp = kp;
    pid->ki = ki;
    pid->kd = kd;
    pid->integrator = 0.0f;
    pid->prev_error = 0.0f;
    pid->out_min = out_min;
    pid->out_max = out_max;
    pid->i_min = out_min;
    pid->i_max = out_max;
}

void pid_reset(pid_t *pid) {
    pid->integrator = 0.0f;
    pid->prev_error = 0.0f;
}

float pid_update(pid_t *pid, float target, float measurement, float dt_s) {
    float error = target - measurement;
    pid->integrator += error * dt_s * pid->ki;
    pid->integrator = clampf(pid->integrator, pid->i_min, pid->i_max);
    float derivative = dt_s > 0.0f ? (error - pid->prev_error) / dt_s : 0.0f;
    pid->prev_error = error;
    float out = pid->kp * error + pid->integrator + pid->kd * derivative;
    return clampf(out, pid->out_min, pid->out_max);
}
