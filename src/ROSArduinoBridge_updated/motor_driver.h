/***************************************************************
   Motor driver function definitions - by James Nugen
   *************************************************************/

#ifdef L298_MOTOR_DRIVER
  #define RIGHT_MOTOR_BACKWARD 5
  #define LEFT_MOTOR_BACKWARD  6
  #define RIGHT_MOTOR_FORWARD  9
  #define LEFT_MOTOR_FORWARD   10
  #define RIGHT_MOTOR_ENABLE 12
  #define LEFT_MOTOR_ENABLE 13
#endif

// --- NEW SECTION FOR ESP32 + CYTRON ---
#ifdef CYTRON_MOTOR_DRIVER
  // Replace these numbers with your actual ESP32 GPIO pins!
  #define LEFT_MOTOR_PWM   12 // PWM Pin for Left Motor
  #define LEFT_MOTOR_DIR   26 // DIR Pin for Left Motor
  
  #define RIGHT_MOTOR_PWM 32// PWM Pin for Right Motor
  #define RIGHT_MOTOR_DIR  33// DIR Pin for Right Motor
#endif
// --------------------------------------

void initMotorController();
void setMotorSpeed(int i, int spd);
void setMotorSpeeds(int leftSpeed, int rightSpeed);
