/* Float PID Controller - Corrected Incremental Form
   Formula: Output += (Kp * DeltaError) + (Ki * Error) + (Kd * DeltaInput)
*/

typedef struct {
  float TargetTicksPerFrame;    
  long Encoder;                 
  long PrevEnc;                 
  
  float err;
  float prevErr;
  float inputFiltered;          
  float prevInput; // Needed for Derivative
  
  float output; 
} SetPointInfo;

SetPointInfo leftPID, rightPID;

// --- TUNING PARAMETERS ---
// Start with Kp=1.0, Ki=0.5, Kd=0.0
float Kp = 2.0f;  
float Ki = 0.1f; 
float Kd = 0.04f;

// Filter Consts
const float inputAlpha = 0.3f; 

unsigned char moving = 0; 
unsigned char was_moving = 0;

void resetPID(){
   leftPID.TargetTicksPerFrame = 0.0;
   leftPID.Encoder = readEncoder(LEFT);
   leftPID.PrevEnc = leftPID.Encoder;
   leftPID.prevErr = 0;
   leftPID.inputFiltered = 0;
   leftPID.prevInput = 0;
   leftPID.output = 0;
   
   rightPID.TargetTicksPerFrame = 0.0;
   rightPID.Encoder = readEncoder(RIGHT);
   rightPID.PrevEnc = rightPID.Encoder;
   rightPID.prevErr = 0;
   rightPID.inputFiltered = 0;
   rightPID.prevInput = 0;
   rightPID.output = 0;
}

void doPID(SetPointInfo * p) {
  // 1. Calculate Raw Speed
  float inputRaw = p->Encoder - p->PrevEnc;
  p->PrevEnc = p->Encoder; 

  // 2. Filter Speed
  p->inputFiltered = inputAlpha * inputRaw + (1.0f - inputAlpha) * p->inputFiltered;

  // 3. Calculate Error
  p->err = p->TargetTicksPerFrame - p->inputFiltered;

  // --- INCREMENTAL PID MATH ---
  
  // P-Term: Reacts to CHANGE in error (The "Kick")
  float P_change = Kp * (p->err - p->prevErr);
  
  // I-Term: Reacts to ERROR existence (The "Push")
  // Since we add this to 'output' every loop, it acts as the Integrator.
  float I_change = Ki * p->err;
  
  
  // D-Term: Reacts to change in measurement (Dampening)
  // (Using input instead of error avoids "Derivative Kick" on target change)
  float D_change = Kd * (p->prevInput - p->inputFiltered);

  // 4. Update Accumulator
  p->output += P_change + I_change + D_change;

  // 5. Save History
  p->prevErr = p->err;
  p->prevInput = p->inputFiltered;

  // 6. Clamp Final Output
  if (p->output > MAX_PWM) p->output = MAX_PWM;
  if (p->output < -MAX_PWM) p->output = -MAX_PWM;
}

void updatePID() {
  leftPID.Encoder = readEncoder(LEFT);
  rightPID.Encoder = readEncoder(RIGHT);
  
  if (!moving){
    // Keep resetting so 'PrevEnc' tracks the wheel even if you push it by hand
    resetPID(); 
    // was_moving = 0;
    return;
  }

  // --- THE FIX: Detect Start-up ---
  // If we weren't moving last loop, but we ARE moving now...
  // if (was_moving == 0) {
  //     // 1. Wipe all old P/I/D terms
  //     resetPID(); 
      
  //     // 2. Pre-load the error so we don't get a "Jump"
  //     // This cheats and says "The previous error was exactly what we have now"
  //     leftPID.prevErr = leftPID.TargetTicksPerFrame;
  //     rightPID.prevErr = rightPID.TargetTicksPerFrame;
  // }
  // was_moving = 1;

  doPID(&rightPID);
  doPID(&leftPID);

  // --- DEBUG LOGS ---
  // Comment these out when connecting to ROS!
  // Serial.print("Target1:");
  // Serial.print(rightPID.TargetTicksPerFrame); 
  // Serial.print(" Actual1:");
  // Serial.print(rightPID.inputFiltered); 
  // Serial.print(" PWM:");
  // Serial.println(rightPID.output); 
  // Serial.print("Target2:");
  // Serial.print(leftPID.TargetTicksPerFrame); 
  // Serial.print(" Actual2:");
  // Serial.print(leftPID.inputFiltered); 
  // Serial.print(" PWM2:");
  // Serial.println(leftPID.output); 
  // ------------------

  setMotorSpeeds((int)leftPID.output, (int)rightPID.output);
}