/* *************************************************************
   Encoder driver function definitions - by James Nugen
   ************************************************************ */
   
// --- NEW SECTION FOR ESP32 ---
#ifdef ARDUINO_ARCH_ESP32
  // Change these numbers to match your ESP32 Wiring!
  #define LEFT_ENC_PIN_A   14 // Left Motor Phase A
  #define LEFT_ENC_PIN_B  27// Left Motor Phase B
  
  #define RIGHT_ENC_PIN_A 13 // Right Motor Phase A
  #define RIGHT_ENC_PIN_B 25 // Right Motor Phase B
#endif
// -----------------------------
   
long readEncoder(int i);
void resetEncoder(int i);
void resetEncoders();