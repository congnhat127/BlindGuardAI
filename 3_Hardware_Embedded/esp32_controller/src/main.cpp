#include <Arduino.h>

// TODO: Include các thư viện cần thiết
// #include <TinyGPSPlus.h>
// #include <FastLED.h>

void setup() {
  // Khởi tạo Serial để debug
  Serial.begin(115200);
  Serial.println("Khởi động BlindGuard ESP32 Controller...");

  // TODO: Khởi tạo các chân GPIO cho LED, Loa, Giao tiếp UART với Jetson
  // pinMode(LED_PIN, OUTPUT);
}

void loop() {
  // 1. Lắng nghe tín hiệu cảnh báo (BSRI) từ Jetson gửi xuống qua Serial/UART
  if (Serial.available() > 0) {
    String data = Serial.readStringUntil('\n');
    // Phân tích dữ liệu JSON hoặc chuỗi để lấy mức độ cảnh báo
    // Kích hoạt LED/Loa tương ứng
  }

  // 2. Đọc dữ liệu GPS (nếu được kết nối trực tiếp với ESP32)
  // 3. Gửi dữ liệu trạng thái ngược lại Jetson hoặc lên Cloud

  delay(10); // Giảm tải CPU
}
