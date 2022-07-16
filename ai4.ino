int sensorPins[] = {A1,A2,A3,A4};    // select the input pin for the potentiometer

void setup() {
  Serial.begin(57600);
}

void loop() {
  for(int i = 0; i < 4; i++) {
    Serial.print(analogRead(sensorPins[i]));
    Serial.print(",");
  }
  Serial.println("1024");  
  delay(100);
}
