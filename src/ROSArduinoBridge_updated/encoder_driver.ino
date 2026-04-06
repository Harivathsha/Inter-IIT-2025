#ifdef USE_BASE

#ifdef ARDUINO_ARCH_ESP32
  // We need volatile variables for the ISRs
  volatile long left_enc_pos = 0L;
  volatile long right_enc_pos = 0L;
  
  // State variables for the State Machine
  volatile uint8_t prevLeftState = 0;
  volatile uint8_t prevRightState = 0;

  // --- LEFT ENCODER ISR (INVERTED) ---
  // Swapped ++ and -- so it counts properly for the left side
  void IRAM_ATTR leftEncoderISR() {
    uint8_t state = (digitalRead(LEFT_ENC_PIN_A) << 1) | digitalRead(LEFT_ENC_PIN_B);

    if ((prevLeftState == 0b00 && state == 0b01) ||
        (prevLeftState == 0b01 && state == 0b11) ||
        (prevLeftState == 0b11 && state == 0b10) ||
        (prevLeftState == 0b10 && state == 0b00))
      left_enc_pos--; // <--- CHANGED TO DECREMENT
    else if ((prevLeftState == 0b00 && state == 0b10) ||
             (prevLeftState == 0b10 && state == 0b11) ||
             (prevLeftState == 0b11 && state == 0b01) ||
             (prevLeftState == 0b01 && state == 0b00))
      left_enc_pos++; // <--- CHANGED TO INCREMENT

    prevLeftState = state;
  }

  // --- RIGHT ENCODER ISR (STANDARD) ---
  void IRAM_ATTR rightEncoderISR() {
    uint8_t state = (digitalRead(RIGHT_ENC_PIN_A) << 1) | digitalRead(RIGHT_ENC_PIN_B);

    if ((prevRightState == 0b00 && state == 0b01) ||
        (prevRightState == 0b01 && state == 0b11) ||
        (prevRightState == 0b11 && state == 0b10) ||
        (prevRightState == 0b10 && state == 0b00))
      right_enc_pos++;
    else if ((prevRightState == 0b00 && state == 0b10) ||
             (prevRightState == 0b10 && state == 0b11) ||
             (prevRightState == 0b11 && state == 0b01) ||
             (prevRightState == 0b01 && state == 0b00))
      right_enc_pos--;

    prevRightState = state;
  }
  
  /* Wrap the encoder reading function */
  long readEncoder(int i) {
    if (i == LEFT) return left_enc_pos;
    else return right_enc_pos;
  }

  /* Wrap the encoder reset function */
  void resetEncoder(int i) {
    if (i == LEFT) left_enc_pos = 0L;
    else right_enc_pos = 0L;
  }
  
  void initEncoders(){
    pinMode(LEFT_ENC_PIN_A, INPUT); 
    pinMode(LEFT_ENC_PIN_B, INPUT);
    pinMode(RIGHT_ENC_PIN_A, INPUT);
    pinMode(RIGHT_ENC_PIN_B, INPUT);
    
    // Read initial state
    prevLeftState = (digitalRead(LEFT_ENC_PIN_A) << 1) | digitalRead(LEFT_ENC_PIN_B);
    prevRightState = (digitalRead(RIGHT_ENC_PIN_A) << 1) | digitalRead(RIGHT_ENC_PIN_B);

    // Attach CHANGE interrupt to BOTH pins for 4x Resolution
    attachInterrupt(digitalPinToInterrupt(LEFT_ENC_PIN_A), leftEncoderISR, CHANGE);
    attachInterrupt(digitalPinToInterrupt(LEFT_ENC_PIN_B), leftEncoderISR, CHANGE);
    attachInterrupt(digitalPinToInterrupt(RIGHT_ENC_PIN_A), rightEncoderISR, CHANGE);
    attachInterrupt(digitalPinToInterrupt(RIGHT_ENC_PIN_B), rightEncoderISR, CHANGE);
  }
  
#endif

void resetEncoders() {
  resetEncoder(LEFT);
  resetEncoder(RIGHT);
}

#endif