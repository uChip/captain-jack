Thinking about captain jack's movements.
There are really two paths or movement controls happening in parallel.

One path is beak movement.  The current thinking is that HAIKU generates a textual response, the TTS engine turns that response into an audio stream, a program looks at the audio stream and generates beak positions, beak positions are turned into commands sent to the Arduino, Arduino commands are turned into calls to the servo driver. [refine this if it changes or if it is just wrong] Timing is inherant.  The beak needs to be in sync with the audio.  This probably requires that audio be delayed by some amount to account for command transfer, real-time processing and mechanical response times.

There is another path for the head movement.  Head position and movement may be influenced by DoA, inferred from text content, by explicit tags in the text stream, or in some cases are just random.  By whatever means they are triggered movement starts as a gesture, a short set of predetermined commands that are not just a head position, but could include multiple positions in a timed sequence.
 - This implies that commands are not just servo positions, but have a time component as well.
To have realistic (lifelike) movement the pitch (head nod up and down), roll (head tips side to side), and yaw (head rotates side to side) have to be synchronized and eased.  An easing library is available on the Arduino that overlays the servo library.  
 - The easing library can sychronize multi-servo movement. 
 - The servo easing library and the software serial library sometimes interfere with each other. We removed software serial when we removed the MY1690.  Don't add it back in without reseaching more on the interference.
 - Servo control is a PWM signal with a 20ms period.  Changes more frequently than every 20ms will be lost.
   - Implies Arduino real-time loop need be no faster than 20ms and could perhaps be slower.  Needs more research. Remember servo ease update call requirements.
 - Easing entails multiple math operations (for cubic) for each servo at each easing update.  Keep things fast.  Keep to integer as much as posible.  May need to rework easing library.
 - While keeping commands human readable is important, keep them short and easily parsable for speed.
   - For instance, although roll and pitch may contain angles of over 100 degrees (3 digits) actual movement is less than 100 degrees.  Use 2 digits and offset.
 - Use higher speeds to keep communication time low.
 - Open questions:
   - Are gestures stored on the Arduino or the Pi? i.e. does Arduino interpret gestures or take basic servo move commands.
   - Are gestures interruptable? Does arrival or trigger of a new command before the current command finishes preempt or wait?
   - Are gestures layerable or blendable?
   - Does beak movement need easing?
   - Is 20ms fast enough? And will easing slow head movement down too much?


