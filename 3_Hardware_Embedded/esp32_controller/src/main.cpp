/**
 * ----------------------------------------------------------------------------
 * Project: BlindGuard AI - Heavy Truck Blind-Spot Safety System
 * Firmware: ESP32 Hardware Warning & Sensor Hub Controller
 * Board: ESP32 NodeMCU / DevKit V1
 * Communication: High-speed UART with NVIDIA Jetson Nano B01 (115200 baud)
 * Standards: ISO 8855, ISO 15623, UNECE R151 / R158 / R159
 * ----------------------------------------------------------------------------
 */

#include <Arduino.h>
#include <TinyGPSPlus.h>
#include <FastLED.h>

// ==================== CẤU HÌNH PHẦN CỨNG & CHÂN GPIO ====================
// UART0 (Serial): Giao tiếp với Jetson Nano (TX0 = GPIO1, RX0 = GPIO3)
#define JETSON_SERIAL Serial
#define JETSON_BAUD 115200

// UART2 (Serial2): Kết nối GPS u-blox NEO-6M / NEO-M8N
#define GPS_RX_PIN 16
#define GPS_TX_PIN 17
#define GPS_BAUD 9600
HardwareSerial GPSSerial(2);
TinyGPSPlus gps;

// Còi hú & Buzzer cảnh báo
#define BUZZER_PIN 25           // Chân điều khiển Buzzer thụ động (PWM) hoặc còi xe
#define BUZZER_CHANNEL 0
#define BUZZER_PWM_FREQ 2400    // Tần số còi chíp 2.4 kHz (gây chú ý tối ưu)

// Đèn LED cảnh báo RGB (FastLED WS2812B trên cột chữ A hoặc gương phụ)
#define NUM_LEDS 8
#define LED_DATA_PIN 27
#define LED_COLOR_ORDER GRB
#define LED_CHIPSET WS2812B
CRGB leds[NUM_LEDS];

// Đèn LED chỉ thị mức rủi ro rời rạc (tùy chọn gắn taplo)
#define PIN_LED_GREEN  18  // Mức 0: SAFE
#define PIN_LED_YELLOW 19  // Mức 1: CAUTION
#define PIN_LED_ORANGE 21  // Mức 2: WARNING
#define PIN_LED_RED    22  // Mức 3: CRITICAL

// Tín hiệu cảm biến công tắc xe (Optocoupler cách ly 24V -> 3.3V)
#define PIN_SIGNAL_LEFT   32  // Xi-nhan trái
#define PIN_SIGNAL_RIGHT  33  // Xi-nhan phải
#define PIN_REVERSE_GEAR  34  // Số lùi (R)

// ==================== KHAI BÁO BIẾN TRẠNG THÁI ====================
enum RiskLevel {
    RISK_SAFE = 0,
    RISK_CAUTION = 1,
    RISK_WARNING = 2,
    RISK_CRITICAL = 3
};

struct WarningState {
    RiskLevel level = RISK_SAFE;
    float bsri_score = 0.0f;
    int track_id = 0;
    int zone_id = 0;
    float ttc_sec = -1.0f;
    unsigned long last_packet_time = 0;
} currentWarning;

struct EgoSensors {
    float speed_mps = 0.0f;
    float yaw_rate_rad_s = 0.0f;
    char turn_signal[8] = "OFF";
    char gear[4] = "D";
    unsigned long last_send_time = 0;
} egoSensors;

// Cấu hình nhịp còi & chớp đèn
unsigned long lastBuzzerToggle = 0;
bool buzzerState = false;
const unsigned long HEARTBEAT_TIMEOUT_MS = 800; // Tự động ngắt cảnh báo nếu Jetson mất kết nối

// ==================== CÁC HÀM TIỆN ÍCH PROTOCOL ====================
uint8_t calculate_checksum(const char* sentence) {
    uint8_t cs = 0;
    for (int i = 0; sentence[i] != '\0' && sentence[i] != '*'; i++) {
        cs ^= (uint8_t)sentence[i];
    }
    return cs;
}

// ==================== THIẾT LẬP BAN ĐẦU (SETUP) ====================
void setup() {
    JETSON_SERIAL.begin(JETSON_BAUD);
    GPSSerial.begin(GPS_BAUD, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);

    // Cấu hình chân LED rời
    pinMode(PIN_LED_GREEN, OUTPUT);
    pinMode(PIN_LED_YELLOW, OUTPUT);
    pinMode(PIN_LED_ORANGE, OUTPUT);
    pinMode(PIN_LED_RED, OUTPUT);

    // Cấu hình chân tín hiệu xe
    pinMode(PIN_SIGNAL_LEFT, INPUT_PULLDOWN);
    pinMode(PIN_SIGNAL_RIGHT, INPUT_PULLDOWN);
    pinMode(PIN_REVERSE_GEAR, INPUT_PULLDOWN);

    // Cấu hình Buzzer PWM
    ledcSetup(BUZZER_CHANNEL, BUZZER_PWM_FREQ, 8);
    ledcAttachPin(BUZZER_PIN, BUZZER_CHANNEL);
    ledcWrite(BUZZER_CHANNEL, 0);

    // Cấu hình FastLED
    FastLED.addLeds<LED_CHIPSET, LED_DATA_PIN, LED_COLOR_ORDER>(leds, NUM_LEDS);
    FastLED.setBrightness(180);
    fill_solid(leds, NUM_LEDS, CRGB::Green);
    FastLED.show();

    digitalWrite(PIN_LED_GREEN, HIGH);
    currentWarning.last_packet_time = millis();

    // Bíp test còi khởi động
    ledcWrite(BUZZER_CHANNEL, 128);
    delay(100);
    ledcWrite(BUZZER_CHANNEL, 0);
}

// ==================== CẬP NHẬT CẢM BIẾN XE & GPS ====================
void update_vehicle_sensors() {
    // 1. Đọc GPS stream
    while (GPSSerial.available() > 0) {
        gps.encode(GPSSerial.read());
    }

    if (gps.speed.isValid()) {
        egoSensors.speed_mps = (float)gps.speed.mps();
    }

    // 2. Đọc xi-nhan và số lùi
    bool sig_left = digitalRead(PIN_SIGNAL_LEFT) == HIGH;
    bool sig_right = digitalRead(PIN_SIGNAL_RIGHT) == HIGH;
    bool rev_gear = digitalRead(PIN_REVERSE_GEAR) == HIGH;

    if (sig_left && sig_right) {
        strcpy(egoSensors.turn_signal, "HAZARD");
    } else if (sig_left) {
        strcpy(egoSensors.turn_signal, "LEFT");
    } else if (sig_right) {
        strcpy(egoSensors.turn_signal, "RIGHT");
    } else {
        strcpy(egoSensors.turn_signal, "OFF");
    }

    if (rev_gear) {
        strcpy(egoSensors.gear, "R");
    } else {
        strcpy(egoSensors.gear, "D");
    }
}

// ==================== GỬI TRẠNG THÁI EGO LÊN JETSON ====================
void send_ego_state_to_jetson() {
    unsigned long now = millis();
    if (now - egoSensors.last_send_time < 50) return; // Tần số 20Hz
    egoSensors.last_send_time = now;

    char buffer[96];
    snprintf(buffer, sizeof(buffer), "EGO,%.2f,%.3f,%s,%s",
             egoSensors.speed_mps,
             egoSensors.yaw_rate_rad_s,
             egoSensors.turn_signal,
             egoSensors.gear);

    uint8_t cs = calculate_checksum(buffer);
    JETSON_SERIAL.printf("$%s*%02X\r\n", buffer, cs);
}

// ==================== NHẬN GÓI BSRI TỪ JETSON ====================
// Cú pháp: $BSRI,<level>,<score>,<track_id>,<zone_id>,<ttc_x10>*<CS>
// Ví dụ:   $BSRI,3,0.88,5,1,12*5A
void parse_jetson_packet(const String& line) {
    if (!line.startsWith("$BSRI,") && !line.startsWith("BSRI,")) return;

    int starIndex = line.indexOf('*');
    String body = line;
    if (body.startsWith("$")) body = body.substring(1);
    if (starIndex > 0) body = line.substring(line.startsWith("$") ? 1 : 0, starIndex);

    int level = 0, track_id = 0, zone_id = 0, ttc_int = -1;
    float score = 0.0f;

    int matched = sscanf(body.c_str(), "BSRI,%d,%f,%d,%d,%d",
                         &level, &score, &track_id, &zone_id, &ttc_int);

    if (matched >= 2) {
        currentWarning.level = (RiskLevel)constrain(level, 0, 3);
        currentWarning.bsri_score = score;
        currentWarning.track_id = track_id;
        currentWarning.zone_id = zone_id;
        currentWarning.ttc_sec = (ttc_int >= 0) ? (ttc_int / 10.0f) : -1.0f;
        currentWarning.last_packet_time = millis();
    }
}

// ==================== THI KÈM CHẾ ĐỘ CÒI & ĐÈN ====================
void execute_warning_actuators() {
    unsigned long now = millis();

    // Heartbeat Watchdog an toàn: nếu Jetson không gửi gì trong 800ms -> về SAFE
    if (now - currentWarning.last_packet_time > HEARTBEAT_TIMEOUT_MS) {
        currentWarning.level = RISK_SAFE;
        currentWarning.bsri_score = 0.0f;
    }

    // Tắt hết LED rời
    digitalWrite(PIN_LED_GREEN, LOW);
    digitalWrite(PIN_LED_YELLOW, LOW);
    digitalWrite(PIN_LED_ORANGE, LOW);
    digitalWrite(PIN_LED_RED, LOW);

    switch (currentWarning.level) {
        case RISK_SAFE:
            digitalWrite(PIN_LED_GREEN, HIGH);
            ledcWrite(BUZZER_CHANNEL, 0); // Tắt còi
            fill_solid(leds, NUM_LEDS, CRGB::Green);
            FastLED.show();
            break;

        case RISK_CAUTION:
            digitalWrite(PIN_LED_YELLOW, HIGH);
            ledcWrite(BUZZER_CHANNEL, 0); // Không hú còi, chỉ báo đèn vàng
            fill_solid(leds, NUM_LEDS, CRGB(255, 200, 0));
            FastLED.show();
            break;

        case RISK_WARNING:
            digitalWrite(PIN_LED_ORANGE, HIGH);
            // Còi bíp ngắt quãng vừa phải (chu kỳ 300ms)
            if (now - lastBuzzerToggle >= 150) {
                lastBuzzerToggle = now;
                buzzerState = !buzzerState;
                ledcWrite(BUZZER_CHANNEL, buzzerState ? 120 : 0);
            }
            // Đèn LED cam nhấp nháy
            fill_solid(leds, NUM_LEDS, buzzerState ? CRGB(255, 120, 0) : CRGB::Black);
            FastLED.show();
            break;

        case RISK_CRITICAL:
            digitalWrite(PIN_LED_RED, HIGH);
            // Còi bíp dồn dập tần số cao hoặc rú liên tục khi TTC < 1s
            if (currentWarning.ttc_sec > 0 && currentWarning.ttc_sec < 1.0f) {
                ledcWrite(BUZZER_CHANNEL, 220); // Rú liên tục âm lượng lớn
                fill_solid(leds, NUM_LEDS, CRGB::Red);
            } else {
                if (now - lastBuzzerToggle >= 80) { // Chu kỳ 160ms dồn dập
                    lastBuzzerToggle = now;
                    buzzerState = !buzzerState;
                    ledcWrite(BUZZER_CHANNEL, buzzerState ? 200 : 0);
                }
                fill_solid(leds, NUM_LEDS, buzzerState ? CRGB::Red : CRGB::Black);
            }
            FastLED.show();
            break;
    }
}

// ==================== VÒNG LẶP CHÍNH (LOOP) ====================
void loop() {
    // 1. Nhận gói BSRI từ Jetson qua Serial
    while (JETSON_SERIAL.available() > 0) {
        String line = JETSON_SERIAL.readStringUntil('\n');
        line.trim();
        if (line.length() > 0) {
            parse_jetson_packet(line);
        }
    }

    // 2. Cập nhật cảm biến xe
    update_vehicle_sensors();

    // 3. Gửi telemetry xe lên Jetson
    send_ego_state_to_jetson();

    // 4. Thực thi còi/đèn cảnh báo
    execute_warning_actuators();

    delay(5); // Nhường chu kỳ CPU
}
