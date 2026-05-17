#include "main.h"
#include "wheel_app.h"

extern CAN_HandleTypeDef hcan1;
extern UART_HandleTypeDef huart3;
static wheel_app_t g_wheel;

static void CAN1_Filter_Init(void) {
    CAN_FilterTypeDef filter = {0};
    filter.FilterBank = 0;
    filter.FilterMode = CAN_FILTERMODE_IDMASK;
    filter.FilterScale = CAN_FILTERSCALE_32BIT;
    filter.FilterIdHigh = (0x205U << 5);
    filter.FilterIdLow = 0;
    filter.FilterMaskIdHigh = (0x7FFU << 5);
    filter.FilterMaskIdLow = 0;
    filter.FilterFIFOAssignment = CAN_FILTER_FIFO0;
    filter.FilterActivation = ENABLE;
    HAL_CAN_ConfigFilter(&hcan1, &filter);
}

int main(void) {
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();
    MX_CAN1_Init();
    MX_USART3_UART_Init();

    CAN1_Filter_Init();
    HAL_CAN_Start(&hcan1);
    HAL_CAN_ActivateNotification(&hcan1, CAN_IT_RX_FIFO0_MSG_PENDING);
    wheel_app_init(&g_wheel, &hcan1, &huart3);
    wheel_app_start(&g_wheel);

    while (1) {
        wheel_app_tick(&g_wheel, HAL_GetTick());
    }
}

void HAL_CAN_RxFifo0MsgPendingCallback(CAN_HandleTypeDef *hcan) {
    CAN_RxHeaderTypeDef hdr;
    uint8_t data[8];
    if (hcan == &hcan1 && HAL_CAN_GetRxMessage(hcan, CAN_RX_FIFO0, &hdr, data) == HAL_OK) {
        wheel_app_on_can_rx(&g_wheel, &hdr, data);
    }
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart) {
    if (huart == &huart3) {
        wheel_app_on_uart_byte(&g_wheel, g_wheel.uart_byte);
        HAL_UART_Receive_IT(&huart3, &g_wheel.uart_byte, 1);
    }
}
