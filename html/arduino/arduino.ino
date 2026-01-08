//#include <Arduino.h>
#include <LiquidCrystal.h>
#include <Servo.h>
#include <IRremote.h>

// DIODA RGB
int RED = 3;
int GREEN = 6;
int BLUE = 5;
// POLICE SIGNAL
int policeBLUE = 13;
int policeRED = A5;
// SERWO
int SERWO = 9;
Servo myServo;
// BUZZER
int BUZZER = 10;
// LCD
const int rs = 2, en = 4, d4 = 7, d5 = 8, d6 = 11, d7 = 12;
LiquidCrystal lcd(rs,en,d4,d5,d6,d7);
// ALKOHOL MQ-3
int ALKOHOL = A0;
// CZUJNIK SWIATLA LM393
int LIGHT = A1;
// CZUJNIK PIR (kulka)
int PIR = A2;
// CZUJNIK ODBICIOWY IR LM393
int IR_OBST = A3;
// CZUJNIK PODCZERWIENI IR
int IR_RECV = A4;

// INNE ZMIENNE
int currR = 0;
int currG = 0;
int currB = 0;

int isOn = 0;
unsigned long Command = 0;

unsigned long colorTimer = 0;
unsigned long serialTimer = 0;
unsigned long proximityTimer = 0;
unsigned long motionTimer = 0;

unsigned long antyPilot = 0;

bool buzzerActive = false;

int alarm = LOW;
int sound = LOW;

int step = 0;
int curr = 0;
int next = 1;

int lcdCount;

unsigned long pwmMicros = 0;
int redTargetVal = 0;

byte colors[11][3] = {
  {255, 0, 0},    // 1. Red
  {255, 165, 0},  // 2. Orange
  {255, 255, 0},  // 3. Yellow
  {0, 255, 0},    // 4. Green
  {0, 255, 0},
  {0, 255, 127},
  {0, 255, 255},  // 5. Aqua
  {0, 0, 255},    // 6. Blue
  {128, 0, 128},  // 7. Purple
  {255, 0, 255},  // 8. Pink
  {255, 255, 255} // 9. White
};

void setup() {
  Serial.begin(9600);

  IrReceiver.begin(IR_RECV, DISABLE_LED_FEEDBACK);

  myServo.attach(SERWO);

  pinMode(RED, OUTPUT);
  pinMode(GREEN, OUTPUT);
  pinMode(BLUE, OUTPUT);

  pinMode(policeBLUE, OUTPUT);
  pinMode(policeRED, OUTPUT);

  pinMode(ALKOHOL, INPUT);

  pinMode(LIGHT, INPUT);
  
  pinMode(PIR, INPUT);

  pinMode(IR_OBST, INPUT);

  pinMode(BUZZER, OUTPUT);

  lcd.begin(16, 2);
  // Serial.println("---- ARDUINO ON ----"); 

}

void loop() {

  // 1. RGB RED(3) DIODE REPAIR DUE TO IR RECEIVER MODULE
  unsigned long currentMicros = micros();
  if (currentMicros - pwmMicros >= 4000) { // Cykl 4ms (250Hz)
    pwmMicros = currentMicros;
  }
  // Symulacja analogWrite na cyfrowym pinie
  if ((currentMicros - pwmMicros) < map(redTargetVal, 0, 255, 0, 4000)) {
    digitalWrite(RED, HIGH);
  } else {
    digitalWrite(RED, LOW);
  }

  // 2. IR RECEIVER MODULE
  if (IrReceiver.decode()) {
    if (IrReceiver.decodedIRData.protocol == NEC) {
      // szum
    }
    if (IrReceiver.decodedIRData.flags & IRDATA_FLAGS_IS_REPEAT){
      if (Command == 0x40) {
        Serial.println(F("---> HOLD ON"));
        myServo.write(180);
        delay(350);
        myServo.write(0);
        delay(350);
      }
      else if (Command == 0x19){
        Serial.println(F("---> HOLD OFF"));
        myServo.write(90);
        delay(250);
        myServo.write(0);
        delay(250);
      }
    }
    else {
      Command = IrReceiver.decodedIRData.command;

      if (Command == 0x40) {
        Serial.println(F("---> PRESSED ON"));
        lcdCount += 1;
        switch(lcdCount) {
          case 1:
          lcd.setCursor(0,0);
          lcd.print("matka ");
          break;
          case 2:
          lcd.print("jest ");
          break;
          case 3:
          lcd.setCursor(0,1);
          lcd.print("wiecznie ");
          break;
          case 4:
          lcd.print("glodna");
          break;
        }
      } 
      else if (Command == 0x19) {
        Serial.println(F("---> PRESSED OFF"));
        lcd.clear();
        lcdCount = 0;
      }
    }
    IrReceiver.resume();
  }
  
  // 3. PROXIMITY DETECTING MODULE
  if (digitalRead(IR_OBST) == LOW) {
    if (antyPilot == 0){
      antyPilot = millis();
    }

    if (millis() - antyPilot > 200) {
      if (millis() - proximityTimer > 150) {
        proximityTimer = millis();

        // buzzerActive = true;

        // if (sound == LOW) {
        //   tone(BUZZER, 2500);
        //   sound = HIGH;
        // }
        // else {
        //   tone(BUZZER,1500);
        //   sound = LOW;
        // }
      }
    }
  }
  else {
    antyPilot = 0;

    // if (digitalRead(IR_OBST) == HIGH) {
    //   if (buzzerActive == true) {
    //     noTone(BUZZER);
    //     IrReceiver.begin(IR_RECV, DISABLE_LED_FEEDBACK);
    //     buzzerActive = false;
    //   }
    // }
  }
  // 4. PIR DETECTING MODULE
  if (digitalRead(PIR) == HIGH) {
    if (millis() - motionTimer > 200) {
      motionTimer = millis();
      
      // if (alarm == LOW){
      //   digitalWrite(policeBLUE, HIGH);
      //   digitalWrite(policeRED, LOW);
      //   alarm = HIGH;
      // }
      // else{
      //   digitalWrite(policeBLUE, LOW);
      //   digitalWrite(policeRED, HIGH);
      //   alarm = LOW;
      // }
    }
  } else {
      digitalWrite(policeBLUE, LOW);
      digitalWrite(policeRED, LOW);
      alarm = LOW;
  }

  // 5. SENSORS OUTPUT MODULE
  if (millis() - serialTimer > 200) {
    serialTimer = millis();
    int alko = analogRead(ALKOHOL);
    int swiatelko = analogRead(LIGHT);
    int proximity = digitalRead(IR_OBST);
    int motion = digitalRead(PIR); 
    Serial.println(String(swiatelko) + "," + String(proximity) + "," + String(motion) + "," + String(alko));
  }

  // 6. RGB DIODE MANAGEMENT MODULE
  // if (millis() - colorTimer > 20) {
  //   colorTimer = millis();

  //   int r = map(step, 0, 100, colors[curr][0], colors[next][0]);
  //   int g = map(step, 0, 100, colors[curr][1], colors[next][1]);
  //   int b = map(step, 0, 100, colors[curr][2], colors[next][2]);

  //   redTargetVal = r;
  //   analogWrite(GREEN, g);
  //   analogWrite(BLUE, b);

  //   step++;
  //   if (step > 100) {
  //     step = 0;
  //     curr++;
  //     next++;
  //     if (curr > 10) curr = 0;
  //     if (next > 10) next = 0;
  //   }
  // }
}