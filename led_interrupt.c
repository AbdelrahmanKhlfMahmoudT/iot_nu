#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <unistd.h>
#include <pigpio.h>

#define LED_PIN     17
#define BUTTON_PIN  27

volatile int led_state = 0;

void button_callback(int gpio, int level, uint32_t tick)
{
    if (level == 0)   // Button pressed
    {
        led_state = !led_state;
        gpioWrite(LED_PIN, led_state);

        printf("Button pressed -> LED %s\n",
               led_state ? "ON" : "OFF");
    }
}

int main(void)
{
    // Initialize pigpio
    if (gpioInitialise() < 0)
    {
        printf("pigpio initialization failed!\n");
        return 1;
    }

    // Configure LED
    gpioSetMode(LED_PIN, PI_OUTPUT);
    gpioWrite(LED_PIN, 0);

    // Configure button
    gpioSetMode(BUTTON_PIN, PI_INPUT);
    gpioSetPullUpDown(BUTTON_PIN, PI_PUD_UP);

    // Configure interrupt on falling edge
    gpioSetISRFunc(
        BUTTON_PIN,
        FALLING_EDGE,
        200,                 // 200 ms debounce
        button_callback
    );

    printf("System ready.\n");
    printf("Press the button to toggle the LED.\n");

    // Keep program running
    while (1)
    {
        sleep(1);
    }

    gpioTerminate();

    return 0;
}
