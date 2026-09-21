/*
  EasingDiagnostic.ino
  2026-09-20 : Chip + Claude

  One-off diagnostic sketch, NOT part of the real firmware. Investigates
  the "discrete steps instead of one smooth move" behavior observed while
  exercising ServoControl.ino against real hardware (see specification.md
  and git history around 2026-09-20).

  Drives a single ServoEasing-controlled servo on the real pitch pin,
  using the exact same setEaseTo()/setEaseToDForAllServos()/
  synchronizeAllServosAndStartInterrupt() call pattern as
  ServoControl.ino's 's' handler, so this exercises the identical code
  path. Instead of relying on a human counting visible steps, it polls
  the servo's own internal current position (in microseconds - finer
  resolution than whole degrees, so degree rounding can't hide real
  updates) every loop iteration and prints a timestamped line to Serial
  every time that value actually changes. This gives an objective trace
  of how often and how smoothly the position really updates.

  Protocol (deliberately minimal, not the real ServoControl.ino syntax):
    send digits followed by 'g' -> triggers one move to the OTHER preset
    target (toggles between two fixed targets, a ~5 degree swing) over
    that many milliseconds. E.g. "2000g" moves over 2000ms.

  Output: "t=<millis>,us=<current_microseconds>" printed once per change,
  plus a "MOVE START"/"MOVE END" marker line around each triggered move.

  Restore arduino/ServoControl/ServoControl.ino to the board when done -
  this sketch is diagnostic only.
*/

#include <Arduino.h>
#include <Servo.h>

#define ENABLE_EASE_CUBIC
#include "ServoEasing.hpp"

const uint8_t SERVO_PITCH_PIN = 3;  // matches ServoControl.ino's real wiring

// Matches ServoControl.ino: PITCH_RESTING=35, PITCH_OFFSET=70 -> 105 is the
// real resting PWM-target angle; +5 degrees (110) matches id-idle-breathing's
// actual swing.
const int TARGET_A = 105;
const int TARGET_B = 110;  // 5-degree swing, matching id-idle-breathing's actual amplitude
// Findings 2026-09-20 (see specification.md Open Issues): with TARGET_B=110
// (5 degrees / ~52us total change), updates land ~every 20-40ms but only
// ~1us apart - visibly stepped on the real bird. With TARGET_B=135 (30
// degrees / ~310us), the same update cadence produces ~3us/update and
// looks smooth. Change TARGET_B to retest at a different distance.

ServoEasing pitchServo;

long targetDuration = 0;
bool haveDuration = false;
bool nextIsA = false;  // start by moving to B first (away from resting)

int lastMicroseconds = -1;

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(5);
  pitchServo.attach(SERVO_PITCH_PIN);
  pitchServo.write(TARGET_A);
  delay(500);
  Serial.println(F("EasingDiagnostic ready. Send e.g. 2000g to trigger a move over 2000ms."));
  lastMicroseconds = pitchServo.getCurrentMicroseconds();
}

void loop() {
  if (Serial.available() > 0) {
    char incomingByte = Serial.read();
    if (incomingByte >= '0' && incomingByte <= '9') {
      if (!haveDuration) {
        targetDuration = 0;
        haveDuration = true;
      }
      targetDuration = targetDuration * 10 + (incomingByte - '0');
    } else if (incomingByte == 'g') {
      int target = nextIsA ? TARGET_A : TARGET_B;
      nextIsA = !nextIsA;
      long duration = haveDuration ? targetDuration : 2000;
      haveDuration = false;

      Serial.print(F("MOVE START target="));
      Serial.print(target);
      Serial.print(F(" duration="));
      Serial.println(duration);

      pitchServo.setEaseTo(target);
      setEaseToDForAllServos(duration);
      synchronizeAllServosAndStartInterrupt();

      unsigned long moveStartMillis = millis();
      lastMicroseconds = pitchServo.getCurrentMicroseconds();
      Serial.print(F("t=0,us="));
      Serial.println(lastMicroseconds);

      while (millis() - moveStartMillis < (unsigned long) duration + 100) {
        int current = pitchServo.getCurrentMicroseconds();
        if (current != lastMicroseconds) {
          Serial.print(F("t="));
          Serial.print(millis() - moveStartMillis);
          Serial.print(F(",us="));
          Serial.println(current);
          lastMicroseconds = current;
        }
      }
      Serial.println(F("MOVE END"));
    }
    // anything else (including a stray 'g' with no digits) is ignored
  }
}
