Thinking about captain jack's movements.
There are really two paths or movement controls happening in parallel.

One path is beak movement.  The current thinking is that HAIKU generates a textual response, the TTS engine turns that response into an audio stream, a program looks at the audio stream and generates beak positions, beak positions are turned into commands sent to the Arduino, Arduino commands are turned into calls to the servo driver. [discuss this if it is inconsistent with other docs] Timing is inherant in the audio stream.  The beak needs to be in sync with the audio.  This probably requires that audio be delayed by some amount to account for RMS processing, command generation and communication, Arduino parsing & easing calculations and mechanical response times.

There is another path for the head movement.  Head position and movement may be influenced by DoA, inferred from text content, by explicit tags in the text stream, or in some cases (idle) are just random.  By whatever means they are triggered movement starts as a gesture, a short set of predetermined commands that are not just a head position, but could include multiple positions in a timed sequence.
 - This implies that commands are not just servo positions, but have a time component as well.
To have realistic (lifelike) movement the pitch (head nod up and down), roll (head tips side to side), and yaw (head rotates side to side) have to be synchronized and eased.  An easing library is available on the Arduino that overlays the servo library.  
 - The easing library can sychronize multi-servo movement. 
 - The servo easing library and the software serial library sometimes interfere with each other. We removed software serial when we removed the MY1690.  Don't add it back in without researching more on the interference.
 - Servo control is a PWM signal with a 20ms period.  Changes more frequently than every 20ms will be lost.
   - Implies Arduino real-time loop need be no faster than 20ms and could perhaps be slower.  Needs more research. Remember servo ease update call requirements.
 - Easing entails multiple math operations (for cubic) for each servo at each easing update.  Keep things fast.  Keep to integer as much as posible.  May need to rework easing library.
 - While keeping commands human readable is important, keep them short and easily parsable for speed.
   - For instance, although roll and pitch may contain angles of over 100 degrees (3 digits) actual movement is less than 100 degrees.  Use 2 digits and offset in Arduino code.
   - Command syntax rules
     - Human readable chars
     - Two chars for beak, pitch and roll angles
     - Three chars for yaw angle
     - Four chars for time.  Time is time to reach the angles in the command, expressed in milliseconds.
     - Single character for field definition (p=pitch,r=roll,y=yaw,b=beak,t=time)
     - No spaces
     - Newline marks end-of-command
 - Use higher speeds to keep communication time low.  Worst case 19 char command = 1.65ms at 115200 bps. [confirm my math]
 - **Reconciled 2026-09-14** (docs/specification.md Open Issues issue 9): this compact syntax is the authoritative wire format, superseding the brief's `HEAD`/`BEAK`/`GESTURE` word-prefixed sketch entirely - see specification.md section 4.13 for the two exact line shapes (head-motion carries p/r/y/t together; beak carries only b, no t, per issue 8's no-easing resolution). The char-count/timing math above still needs re-deriving against that exact format.
 - Open questions:
   - ~~Are gestures stored on the Arduino or the Pi?~~ Resolved 2026-09-14: the Pi, to keep the Arduino as thin as possible. Arduino takes only basic timed servo move commands, never interprets a gesture id. See docs/specification.md, Open Issues issue 7. Accepted implication: if the Pi is down, the Arduino has nothing to fall back on and Jack goes still.
   - Are gestures interruptable? Does arrival or trigger of a new command before the current command finishes preempt or wait?
   - Can gestures include beak movements?
   - Are gestures layerable or blendable?
   - ~~Does beak movement need easing?~~ Resolved 2026-09-14: no separate easing step on either side - smoothing happens as part of the Pi's RMS envelope extraction itself (attack/release-style shaping), and the Arduino applies the BEAK value it receives straight to PWM. See docs/specification.md, Open Issues issue 8 (former).
   - Is 20ms update fast enough? And will easing slow head movement down too much?
   - Need the list of gesture triggers.
   - How robust is serial communications? Is an ACK or timeout retry needed?


