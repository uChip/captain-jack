
/*
  ServoControl.ino
  2026-09-15 : Chip Schnarel

  Reads an incoming text stream and parses the stream to extract commands to control servos.
  Objective is to extract specific servo control commands and ignore malformed strings without
  needing position dependent commands or communications syncing.
  Controls 4 servos, beak, pitch, roll and yaw.
  Beak servo moves immediately upon receipt of the whole command.
  Pitch, roll and yaw move together, synchronized so that they start and finish at the same time,
  taking t milliseconds for the move.
  ServoControl has no way to know if a command is reasonable or not.  It only checks that the
  angle is within the defined range.  Numbers outside the defined range might damage the mechanism, therefore
  angles are limited before being sent to servos.
  Communications stream is receive only, except when DEBUG is defined.
  Servos are not powered up or moved unless SERVO is defined.

  Extracts key characters followed by integers (variable length integer strings terminated by any non-numeric character):
    b<BB>  BB = integer angles in the range of 0 = beak open to 60 = beak fully closed
    p<PP>  PP = integer angles in the range of 0 = head tipped down to 50 = head tipped up
    r<RR>  RR = integer angles in the range of 0 = head tipped to left to 50 = head tipped to right
    y<YY>  YY = integer angles in the range of 0 = head turned to right to 130 = head turned to left
    t<TTTT> TTTT = integer representing milliseconds in the range of 0 = move servos to position immediately to
            9999 = very very very slow movement to position.

  After receiving b and the integer, the angle value is limit checked then sent to the servo subroutine immediately. No easing.
  After receiving p,r,y or t, and the integer, local variables are limit checked and saved.
  After receiving s, a servo ease command is sent using saved values and all three servos are started.
  Sending an s by itself: previous values are sent to ease routine again.
  Any of b, p, r, y, or t commands with integers can be sent individually or concatenated together.
  Sending b, p, r, y, or t with no integer following is the same as sending the character with 0 as the integer.
  All other characters are ignored, including numeric characters not immediately following b, p, r, y or t.
  Line terminators (\r, \n) are also ignored.
  Repeating p, r, y, or t command before sending s will overwrite the previous saved value, not move the servo.
  Integer values are always interpreted as positive.  The negative sign is ignored.
  Angle integer values are saved as data type int.
  
  Examples of valid commands
    b20\n
    p40\n
    r30\n
    y45\n
    t300\n
    s\n
    p40r30y45t300s\n
    b30p40r30y45t300s\n
    p50s\n

  Examples of range adjustments (showing b but p, r and y work the same)
    b75 - parsed as b60
    bX - where X is any non-numeric char except '-' - parsed as b0
    b1025 - parsed as b1
    b-7 - parsed as b7
    b23.4 - parsed as b23

  Stream error examples
    aedfghjkl - ignored. No command char.
    0123456789.23 - ignored. No command char.
    54321b23hpgl - b23 picked out from garbage

  STATUS: Compiles. Runs. Spot checked valid commands work.  Spot checked garbage is ignored.  All done by
  reading debug print statements.  Actual servo response not yet tested.

*/

#include <Arduino.h>
#include <Servo.h>

#define ENABLE_EASE_CUBIC
#include "ServoEasing.hpp"

// --- PIN CONFIGURATION ---
const uint8_t JOYSTICK_ROLL_PIN = A0;
const uint8_t JOYSTICK_PITCH_PIN = A1;
const uint8_t JOYSTICK_YAW_PIN = A2;

const uint8_t SERVO_PITCH_PIN = 3;
const uint8_t SERVO_ROLL_PIN = 5;
const uint8_t SERVO_YAW_PIN = 6;
const uint8_t SERVO_BEAK_PIN = 11;

// --- BEAK SERVO CONFIGURATION ---
const unsigned int BEAK_OPEN = 0;
const unsigned int BEAK_RANGE = 60;
const unsigned int BEAK_OFFSET = 65;

// --- HEAD SERVOS CONFIGURATION ---
const int PITCH_RESTING = 35;   // Servo assembly can result in small differences in alignment. Adjust here to center
const int ROLL_RESTING = 30;    // Servo assembly can result in small errors. Adjust here to center
const int YAW_RESTING = 70;     // Servo assembly can result in small errors. Adjust here to center
const int PITCH_RANGE = 50;     // Servo assembly can result in small errors. Adjust to limit travel
const int ROLL_RANGE = 50;      // Servo assembly can result in small errors. Adjust to limit travel
const int YAW_RANGE = 130;      // Servo assembly can result in small errors. Adjust to limit travel
const int PITCH_OFFSET = 70;    // Servo assembly can result in small errors. Adjust to limit travel
const int ROLL_OFFSET = 55;     // Servo assembly can result in small errors. Adjust to limit travel
const int YAW_OFFSET = 30;      // Servo assembly can result in small errors. Adjust to limit travel

// Slowest gesture in docs/gesture-library.md is a 3-5s sweep; 9999ms gives headroom
// for future gestures while treating anything past it as a garbled command, not a real move.
const long DURATION_MAX = 9999;

Servo beakServo;
ServoEasing pitchServo;
ServoEasing rollServo;
ServoEasing yawServo;

#define DEBUG
#define SERVO

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(5);  // Command transfer times estimated well under 2ms; a 5ms parseInt() timeout firing means something else is wrong.
#if defined(DEBUG)
  Serial.println(F("Just a message at the beginning."));
#endif

#if defined(SERVO)
  //Initialize servos
  beakServo.attach(SERVO_BEAK_PIN);
  beakServo.write(BEAK_RANGE + BEAK_OFFSET);
  pitchServo.attach(SERVO_PITCH_PIN);
  pitchServo.write(PITCH_RESTING + PITCH_OFFSET);
  rollServo.attach(SERVO_ROLL_PIN);
  rollServo.write(ROLL_RESTING + ROLL_OFFSET);
  yawServo.attach(SERVO_YAW_PIN);
  yawServo.write(YAW_RESTING + YAW_OFFSET);
#endif

#if defined(DEBUG)
  delay(500);
  Serial.println(F("Beak open."));
#if defined(SERVO)
  beakServo.write((unsigned int)BEAK_OPEN + BEAK_OFFSET);  // fully open
#endif
  delay(500);
  Serial.println(F("Beak close."));
#if defined(SERVO)
  beakServo.write((unsigned int)BEAK_RANGE + BEAK_OFFSET);
#endif
  delay(500);
  Serial.println(F("Beak open."));
#if defined(SERVO)
  beakServo.write((unsigned int)BEAK_OPEN + BEAK_OFFSET);  // fully open
#endif
  delay(500);
  Serial.println(F("Beak close."));
#if defined(SERVO)
  beakServo.write((unsigned int)BEAK_RANGE + BEAK_OFFSET);
#endif
  delay(500);
#endif
}

unsigned int beakAngle = BEAK_RANGE + BEAK_OFFSET;
unsigned int pitchAngle = PITCH_RESTING + PITCH_OFFSET;
unsigned int rollAngle = ROLL_RESTING + ROLL_OFFSET;
unsigned int yawAngle = YAW_RESTING + YAW_OFFSET;
long duration = 100;

void loop() {
  if (Serial.available() > 0) {  // Data is available to read
    char incomingByte = Serial.read();
#if defined(DEBUG)
    Serial.print(incomingByte);
#endif

    if (incomingByte == 'b') {
      beakAngle = Serial.parseInt(SKIP_NONE, '-');    // don't allow negatives
      if (beakAngle > BEAK_RANGE) beakAngle = BEAK_RANGE;    // Clamp against the defined range, not the offset sum, so the addition below can't wrap
      beakAngle += BEAK_OFFSET;
#if defined(SERVO)
      beakServo.write(beakAngle);
#endif
#if defined(DEBUG)
      Serial.println(beakAngle);
#endif

    } else if (incomingByte == 'p') {
      pitchAngle = Serial.parseInt(SKIP_NONE, '-');
      if (pitchAngle > PITCH_RANGE) pitchAngle = PITCH_RANGE;
      pitchAngle += PITCH_OFFSET;
#if defined(DEBUG)
      Serial.print(pitchAngle);
#endif

    } else if (incomingByte == 'r') {
      rollAngle = Serial.parseInt(SKIP_NONE, '-');
      if (rollAngle > ROLL_RANGE) rollAngle = ROLL_RANGE;
      rollAngle += ROLL_OFFSET;
#if defined(DEBUG)
      Serial.print(rollAngle);
#endif

    } else if (incomingByte == 'y') {
      yawAngle = Serial.parseInt(SKIP_NONE, '-');
      if (yawAngle > YAW_RANGE) yawAngle = YAW_RANGE;
      yawAngle += YAW_OFFSET;
#if defined(DEBUG)
      Serial.print(yawAngle);
#endif

    } else if (incomingByte == 't') {
      duration = Serial.parseInt(SKIP_NONE, '-');
      if (duration > DURATION_MAX) duration = DURATION_MAX;
#if defined(DEBUG)
      Serial.print(duration);
#endif

    } else if (incomingByte == 's') {
#if defined(SERVO)
      pitchServo.setEaseTo(pitchAngle);  // Hmmm, what happens when setEaseTo is sent before current easeTo is finished?
      rollServo.setEaseTo(rollAngle);
      yawServo.setEaseTo(yawAngle);
      setEaseToDForAllServos(duration);
      synchronizeAllServosAndStartInterrupt();
#endif
#if defined(DEBUG)
      Serial.print('\n');
      Serial.print('p');
      Serial.print(pitchAngle);
      Serial.print('r');
      Serial.print(rollAngle);
      Serial.print('y');
      Serial.print(yawAngle);
      Serial.print('t');
      Serial.print(duration);
      Serial.println("Start!");
#endif

    } else {
      // throw away anything else
    }
  }
}
