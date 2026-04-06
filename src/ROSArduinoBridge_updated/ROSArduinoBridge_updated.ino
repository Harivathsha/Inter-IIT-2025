/*********************************************************************
 * ROSArduinoBridge - DEBUG VERSION
 *********************************************************************/

#define USE_BASE      

#ifdef USE_BASE
   #define CYTRON_MOTOR_DRIVER
#endif

#undef USE_SERVOS     

#define BAUDRATE     57600
#define MAX_PWM        255

#if defined(ARDUINO) && ARDUINO >= 100
#include "Arduino.h"
#else
#include "WProgram.h"
#endif

#include "commands.h"
#include "sensors.h"

#ifdef USE_SERVOS
   #include <Servo.h>
   #include "servos.h"
#endif

#ifdef USE_BASE
  #include "motor_driver.h"
  #include "encoder_driver.h"
  #include "diff_controller.h"

  #define PID_RATE           100     
  const int PID_INTERVAL = 1000 / PID_RATE;
  unsigned long nextPID = PID_INTERVAL;
  #define AUTO_STOP_INTERVAL 20000
  long lastMotorCommand = AUTO_STOP_INTERVAL;
#endif

// Variables
int arg = 0;
int arg_index = 0;
char chr;
char cmd;
char argv1[16];
char argv2[16];
long arg1;
long arg2;

void resetCommand() {
  cmd = 0;
  memset(argv1, 0, sizeof(argv1));
  memset(argv2, 0, sizeof(argv2));
  arg1 = 0;
  arg2 = 0;
  arg = 0;
  arg_index = 0;
}

int runCommand() {
  arg1 = atoi(argv1);
  arg2 = atoi(argv2);
  
  // --- DEBUG PRINT (REMOVE LATER) ---
  // This helps us see WHY it thinks 'b' is 'a'
  // Serial.print("DEBUG: Executing CMD [");
  // Serial.write(cmd);
  // Serial.print("] (ASCII ");
  // Serial.print((int)cmd);
  // Serial.print(") with Arg1: ");
  // Serial.println(arg1);
  // ----------------------------------

  switch(cmd) {
  case GET_BAUDRATE:
    Serial.println(BAUDRATE);
    break;
  case ANALOG_READ:
    Serial.println(analogRead(arg1));
    break;
  case DIGITAL_READ:
    Serial.println(digitalRead(arg1));
    break;
  case ANALOG_WRITE:
    Serial.println("OK"); 
    break;
  case DIGITAL_WRITE:
    if (arg2 == 0) digitalWrite(arg1, LOW);
    else if (arg2 == 1) digitalWrite(arg1, HIGH);
    Serial.println("OK"); 
    break;
  case PIN_MODE:
    if (arg2 == 0) pinMode(arg1, INPUT);
    else if (arg2 == 1) pinMode(arg1, OUTPUT);
    Serial.println("OK");
    break;
  case PING:
    Serial.println(Ping(arg1));
    break;
#ifdef USE_SERVOS
  case SERVO_WRITE:
    servos[arg1].setTargetPosition(arg2);
    Serial.println("OK");
    break;
  case SERVO_READ:
    Serial.println(servos[arg1].getServo().read());
    break;
#endif
    
#ifdef USE_BASE
  case READ_ENCODERS:
    Serial.print(readEncoder(LEFT));
    Serial.print(" ");
    Serial.println(readEncoder(RIGHT));
    break;
   case RESET_ENCODERS:
    resetEncoders();
    resetPID();
    Serial.println("OK");
    break;
  case MOTOR_SPEEDS:
    lastMotorCommand = millis();
    if (arg1 == 0 && arg2 == 0) {
      setMotorSpeeds(0, 0);
      resetPID();
      moving = 0;
    }
    else moving = 1;
    leftPID.TargetTicksPerFrame = arg1;
    rightPID.TargetTicksPerFrame = arg2;
    Serial.println("OK"); 
    break;
  case MOTOR_RAW_PWM:
    lastMotorCommand = millis();
    resetPID();
    moving = 0; 
    setMotorSpeeds(arg1, arg2);
    Serial.println("OK"); 
    break;
  case UPDATE_PID:
    {
      char *p = argv1;
      char *str;
      int i = 0;
      float pid_args[3];
      while ((str = strtok_r(p, ":", &p)) != NULL) {
         pid_args[i] = atof(str);
         i++;
      }
      Kp = pid_args[0];
      Kd = pid_args[1];
      Ki = pid_args[2];
      Serial.println("OK");
    }
    break;
#endif
  default:
    Serial.println("Invalid Command");
    break;
  }
  return 0;
}

void setup() {
  Serial.begin(BAUDRATE);
  

  
  delay(2000);
  //Serial.println("ESP32 Ready - Debug Mode");
  resetCommand(); // Ensure variables are clean

#ifdef USE_BASE
  initEncoders(); 
  initMotorController();
  resetPID();
#endif

#ifdef USE_SERVOS
  int i;
  for (i = 0; i < N_SERVOS; i++) {
    servos[i].initServo(
        servoPins[i],
        stepDelay[i],
        servoInitPosition[i]);
  }
#endif
}

void loop() {
  while (Serial.available() > 0) {
    chr = Serial.read();

    if (chr == 10) continue; // Ignore Newline

    if (chr == 13) { // Carriage Return
      if (arg == 1) argv1[arg_index] = 0;
      else if (arg == 2) argv2[arg_index] = 0;
      
      if (cmd > 0) {
        runCommand();
      }
      resetCommand();
    }
    else if (chr == ' ') {
      if (arg == 0) arg = 1;
      else if (arg == 1)  {
        argv1[arg_index] = 0;
        arg = 2;
        arg_index = 0;
      }
      continue;
    }
    else {
      if (arg == 0) {
        cmd = chr;
      }
      else if (arg == 1) {
        argv1[arg_index] = chr;
        arg_index++;
      }
      else if (arg == 2) {
        argv2[arg_index] = chr;
        arg_index++;
      }
    }
  }
  
#ifdef USE_BASE
  if (millis() > nextPID) {
    updatePID();
    nextPID += PID_INTERVAL;
  }
  
  if ((millis() - lastMotorCommand) > AUTO_STOP_INTERVAL) {;
    setMotorSpeeds(0, 0);
    moving = 0;
  }
#endif

#ifdef USE_SERVOS
  int i;
  for (i = 0; i < N_SERVOS; i++) {
    servos[i].doSweep();
  }
#endif
}