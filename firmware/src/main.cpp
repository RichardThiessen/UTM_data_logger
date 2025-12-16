/**
 * UTM Hardware Simulator
 *
 * Simulates a Universal Testing Machine by streaming ASCII float values
 * over both serial ports on the Arduino Due. Format: "{float}\n"
 *
 * Serial Ports:
 *   - Serial    : Programming port (UART via ATmega16U2)
 *   - SerialUSB : Native USB port (direct SAM3X8E USB)
 *
 * Generates test patterns (sine wave, ramp, random walk) with configurable
 * sample rate and pause between tests.
 *
 * LED blinks during active test output.
 */

#include <Arduino.h>

// Configuration - adjust these as needed
const unsigned long SAMPLES_PER_TEST = 100;
const unsigned long SAMPLE_RATE_HZ = 10;        // Samples per second
const unsigned long PAUSE_BETWEEN_TESTS_MS = 2000;

// Derived timing
const unsigned long SAMPLE_INTERVAL_MS = 1000 / SAMPLE_RATE_HZ;

// Pattern types
enum Pattern {
    PATTERN_SINE,
    PATTERN_RAMP,
    PATTERN_RANDOM_WALK,
    PATTERN_COUNT
};

// Current state
Pattern currentPattern = PATTERN_SINE;
unsigned long testCount = 0;

// LED pin (Due has LED on pin 13)
const int LED_PIN = 13;

// Random walk state
float randomWalkValue = 50.0;

/**
 * Generate next sample value based on current pattern
 */
float generateSample(unsigned long sampleIndex, unsigned long totalSamples) {
    float t = (float)sampleIndex / (float)totalSamples;
    float value = 0.0;

    switch (currentPattern) {
        case PATTERN_SINE: {
            // Sine wave with some noise
            float angle = t * 2.0 * PI;
            value = 50.0 + 45.0 * sin(angle);
            value += random(-500, 500) / 100.0;  // +/- 5 noise
            break;
        }

        case PATTERN_RAMP: {
            // Linear ramp from 0 to 100 with noise
            value = t * 100.0;
            value += random(-200, 200) / 100.0;  // +/- 2 noise
            break;
        }

        case PATTERN_RANDOM_WALK: {
            // Random walk
            randomWalkValue += random(-200, 200) / 100.0;
            // Clamp to reasonable range
            if (randomWalkValue < 0) randomWalkValue = 0;
            if (randomWalkValue > 100) randomWalkValue = 100;
            value = randomWalkValue;
            break;
        }

        default:
            value = 50.0;
            break;
    }

    return value;
}

/**
 * Run a single test - output all samples
 */
void runTest() {
    testCount++;

    // Reset random walk for consistent starting point
    randomWalkValue = 50.0;

    // Cycle through patterns
    currentPattern = (Pattern)(testCount % PATTERN_COUNT);

    for (unsigned long i = 0; i < SAMPLES_PER_TEST; i++) {
        // Generate and send sample
        float value = generateSample(i, SAMPLES_PER_TEST);

        // Output as ASCII float with newline to both serial ports
        Serial.println(value, 6);     // Programming port
        SerialUSB.println(value, 6);  // Native USB port

        // Blink LED (on during odd samples)
        digitalWrite(LED_PIN, (i & 1) ? HIGH : LOW);

        // Wait for next sample time
        delay(SAMPLE_INTERVAL_MS);
    }

    // LED off at end of test
    digitalWrite(LED_PIN, LOW);
}

void setup() {
    // Initialize LED
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, LOW);

    // Initialize both serial ports on Arduino Due
    // Serial    = Programming port (UART via ATmega16U2)
    // SerialUSB = Native USB port (direct SAM3X8E USB)
    Serial.begin(9600);
    SerialUSB.begin(9600);

    // Wait for at least one serial connection
    // Don't block forever - continue after timeout if neither connects
    unsigned long startTime = millis();
    while (!Serial && !SerialUSB) {
        if (millis() - startTime > 5000) break;  // 5 second timeout
    }

    // Seed random number generator
    randomSeed(analogRead(0));

    // Brief startup indication
    for (int i = 0; i < 3; i++) {
        digitalWrite(LED_PIN, HIGH);
        delay(100);
        digitalWrite(LED_PIN, LOW);
        delay(100);
    }
}

void loop() {
    // Run a test
    runTest();

    // Pause between tests
    delay(PAUSE_BETWEEN_TESTS_MS);
}
