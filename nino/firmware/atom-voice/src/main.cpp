#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <SPIFFS.h>
#include <FastLED.h>
#include <ArduinoJson.h>
#include <driver/i2s.h>
#include "secrets.h"

constexpr uint32_t RATE = 16000;
constexpr uint32_t MAX_BYTES = RATE * 2 * 30;
constexpr int BUTTON = 39;
constexpr int PIR = 32;
bool lastMotion = false;
uint32_t lastMotionSent = 0;
uint32_t lastSensorSent = 0;
CRGB led[1];
File recording;
uint32_t recorded = 0;
bool recordingNow = false;
bool i2sInstalled = false;
bool lastButton = false;
bool wifiReported = false;
uint32_t lastEdge = 0;

void color(CRGB value) {
  if (led[0] == value) return;
  led[0] = value;
  FastLED.show();
}

bool audioMode(bool mic, uint32_t rate = RATE) {
  if (i2sInstalled) i2s_driver_uninstall(I2S_NUM_0);
  i2sInstalled = false;
  i2s_config_t cfg = {};
  cfg.mode = mic ? (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX | I2S_MODE_PDM)
                 : (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX);
  cfg.sample_rate = rate;
  cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT;
  cfg.channel_format = mic ? I2S_CHANNEL_FMT_ONLY_LEFT : I2S_CHANNEL_FMT_RIGHT_LEFT;
  cfg.communication_format = I2S_COMM_FORMAT_STAND_I2S;
  cfg.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
  cfg.dma_buf_count = 6;
  cfg.dma_buf_len = 256;
  cfg.tx_desc_auto_clear = true;
  if (i2s_driver_install(I2S_NUM_0, &cfg, 0, nullptr) != ESP_OK) return false;
  i2sInstalled = true;
  i2s_pin_config_t pins = {};
  pins.mck_io_num = I2S_PIN_NO_CHANGE;
  pins.bck_io_num = mic ? I2S_PIN_NO_CHANGE : 19;
  pins.ws_io_num = 33;
  pins.data_out_num = mic ? I2S_PIN_NO_CHANGE : 22;
  pins.data_in_num = mic ? 23 : I2S_PIN_NO_CHANGE;
  if (i2s_set_pin(I2S_NUM_0, &pins) != ESP_OK ||
      i2s_set_clk(I2S_NUM_0, rate, I2S_BITS_PER_SAMPLE_16BIT, mic ? I2S_CHANNEL_MONO : I2S_CHANNEL_STEREO) != ESP_OK) {
    i2s_driver_uninstall(I2S_NUM_0);
    i2sInstalled = false;
    return false;
  }
  return true;
}

void stopAudio() {
  if (i2sInstalled) {
    i2s_zero_dma_buffer(I2S_NUM_0);
    i2s_driver_uninstall(I2S_NUM_0);
    i2sInstalled = false;
  }
}

void header(uint8_t* h, uint32_t size) {
  memset(h, 0, 44);
  memcpy(h, "RIFF", 4); memcpy(h + 8, "WAVEfmt ", 8); memcpy(h + 36, "data", 4);
  auto u32 = [&](int p, uint32_t v) { for (int i = 0; i < 4; ++i) h[p + i] = v >> (8 * i); };
  u32(4, size + 36); u32(16, 16); u32(24, RATE); u32(28, RATE * 2); u32(40, size);
  h[20] = 1; h[22] = 1; h[32] = 2; h[34] = 16;
}

bool playReply(const String& route) {
  if (!route.startsWith("/reply/")) return false;
  WiFiClient client;
  HTTPClient http;
  http.setTimeout(60000);
  http.useHTTP10(true);
  const char* keys[] = {"X-Sample-Rate"};
  http.collectHeaders(keys, 1);
  if (!http.begin(client, String(NINO_URL) + route)) return false;
  http.addHeader("Authorization", String("Bearer ") + NINO_TOKEN);
  int status = http.GET();
  if (status != 200) { Serial.printf("Audio HTTP %d\n", status); http.end(); return false; }
  int remaining = http.getSize();
  uint32_t rate = http.header("X-Sample-Rate").toInt();
  if (remaining <= 0 || remaining % 2 || rate < 8000 || rate > 48000 || !audioMode(false, rate)) {
    http.end(); return false;
  }
  color(CRGB::Purple);
  int16_t samples[512];
  int16_t stereo[1024];
  Serial.printf("Reproducao: %d bytes PCM, %u Hz, stereo.\n", remaining, (unsigned)rate);
  Stream* stream = http.getStreamPtr();
  stream->setTimeout(60000);
  bool ok = true;
  while (remaining > 0) {
    size_t wanted = min(remaining, (int)sizeof(samples));
    size_t n = stream->readBytes((char*)samples, wanted);
    if (n != wanted) { ok = false; break; }
    // Voz em volume reduzido; nao gere sinais de teste no alto-falante.
    for (size_t i = 0; i < n / 2; ++i) stereo[2 * i] = stereo[2 * i + 1] = samples[i] / 4;
    size_t written = 0;
    if (i2s_write(I2S_NUM_0, stereo, n * 2, &written, pdMS_TO_TICKS(2000)) != ESP_OK || written != n * 2) {
      ok = false; break;
    }
    remaining -= n;
  }
  delay(100);
  stopAudio();
  http.end();
  Serial.println(ok ? "Reproducao concluida." : "Falha na reproducao.");
  return ok;
}

bool sendRecording() {
  if (WiFi.status() != WL_CONNECTED || recorded < RATE / 2) return false;
  File file = SPIFFS.open("/recording.wav", "r");
  if (!file) return false;
  WiFiClient client;
  HTTPClient http;
  http.setTimeout(60000);
  // HTTP/1.0 permite ler as linhas sem incluir marcadores de Transfer-Encoding.
  http.useHTTP10(true);
  if (!http.begin(client, String(NINO_URL) + "/voice")) { file.close(); return false; }
  http.addHeader("Authorization", String("Bearer ") + NINO_TOKEN);
  http.addHeader("Content-Type", "audio/wav");
  int status = http.sendRequest("POST", &file, file.size());
  file.close();
  if (status != 200) { Serial.printf("HTTP %d\n", status); http.end(); return false; }
  Stream* stream = http.getStreamPtr();
  stream->setTimeout(60000);
  uint32_t start = millis();
  while (millis() - start < 600000 && (http.connected() || stream->available())) {
    String line = stream->readStringUntil('\n');
    if (!line.length()) continue;
    if (line.length() > 8192) { http.end(); return false; }
    DynamicJsonDocument message(8192);
    if (deserializeJson(message, line)) { http.end(); return false; }
    const char* type = message["type"] | "";
    if (!strcmp(type, "error")) {
      Serial.println(message["error"].as<String>()); http.end(); return false;
    }
    if (!strcmp(type, "done")) {
      Serial.println(message["text"].as<String>());
      Serial.println(message["answer"].as<String>());
      String route = message["audio"].isNull() ? "" : message["audio"].as<String>();
      http.end();
      return route.length() ? playReply(route) : true;
    }
  }
  http.end();
  return false;
}

void finishRecording() {
  Serial.printf("Gravacao encerrada: %u bytes.\n", (unsigned)recorded);
  uint8_t h[44]; header(h, recorded);
  bool ok = recording.seek(0) && recording.write(h, sizeof(h)) == sizeof(h);
  recording.close();
  recordingNow = false;
  stopAudio();
  color(CRGB::Blue);
  if (ok) ok = sendRecording();
  SPIFFS.remove("/recording.wav");
  color(ok ? CRGB::Green : CRGB::Red);
  if (!ok) delay(1500);
}

void setup() {
  Serial.begin(115200);
  Serial.println("Nino Atom Voice iniciando.");
  pinMode(BUTTON, INPUT);
  pinMode(PIR, INPUT_PULLDOWN);
  FastLED.addLeds<WS2812, 27, GRB>(led, 1);
  FastLED.setBrightness(64);
  Serial.println("Teste LED GPIO27: vermelho, verde, azul.");
  color(CRGB::Red); delay(400);
  color(CRGB::Green); delay(400);
  color(CRGB::Blue); delay(400);
  color(CRGB::Orange);
  // shortcut: gravacao temporaria na flash, trocar por SD somente com base e pinos confirmados.
  if (!SPIFFS.begin(true)) {
    Serial.println("Falha na flash de gravacao.");
    color(CRGB::Red); while (true) delay(1000);
  }
  Serial.printf("SPIFFS: %u bytes, %u usados.\n", (unsigned)SPIFFS.totalBytes(), (unsigned)SPIFFS.usedBytes());
  if (SPIFFS.exists("/recording.wav")) SPIFFS.remove("/recording.wav");
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

void loop() {
  // Diagnostico USB: reproduz apenas uma resposta autenticada ja gerada pelo Nino.
  if (!recordingNow && Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    if (command.startsWith("play /reply/") && command.length() == 48) {
      playReply(command.substring(5));
    }
  }
  bool motion = digitalRead(PIR) == HIGH;
  if (WiFi.status() == WL_CONNECTED && !recordingNow &&
      (lastSensorSent == 0 || millis() - lastSensorSent >= 30000 || (motion && !lastMotion))) {
    lastSensorSent = millis();
    WiFiClient client;
    HTTPClient http;
    http.setTimeout(2000);
    if (http.begin(client, String(NINO_URL) + "/sensor-status")) {
      http.addHeader("Authorization", String("Bearer ") + NINO_TOKEN);
      http.addHeader("Content-Type", "application/json");
      Serial.printf("Sensor GPIO32: motion=%d HTTP %d\n", motion, http.POST(motion ? "{\"motion\":true}" : "{\"motion\":false}"));
      http.end();
    }
  }
  if (motion && !lastMotion && WiFi.status() == WL_CONNECTED &&
      !recordingNow && (lastMotionSent == 0 || millis() - lastMotionSent >= 15000)) {
    lastMotionSent = millis();
    WiFiClient client;
    HTTPClient http;
    http.setTimeout(2000);
    if (http.begin(client, String(NINO_URL) + "/presence")) {
      http.addHeader("Authorization", String("Bearer ") + NINO_TOKEN);
      Serial.printf("Presenca GPIO32: HTTP %d\n", http.POST(""));
      http.end();
    }
  }
  lastMotion = motion;
  bool pressed = digitalRead(BUTTON) == LOW;
  bool click = pressed && !lastButton && millis() - lastEdge > 200;
  if (pressed != lastButton) {
    Serial.printf("Botao: %s\n", pressed ? "pressionado" : "solto");
    lastButton = pressed;
    if (click) lastEdge = millis();
  }
  if (recordingNow) {
    int16_t samples[512];
    size_t n = 0;
    size_t wanted = min((uint32_t)sizeof(samples), MAX_BYTES - recorded);
    esp_err_t err = i2s_read(I2S_NUM_0, samples, wanted, &n, pdMS_TO_TICKS(100));
    if (err != ESP_OK || n % 2 || recording.write((uint8_t*)samples, n) != n) {
      recording.close(); recordingNow = false; stopAudio(); color(CRGB::Red); delay(1500); return;
    }
    recorded += n;
    if (click || recorded >= MAX_BYTES) finishRecording();
    return;
  }
  if (WiFi.status() != WL_CONNECTED) { wifiReported = false; color(CRGB::Orange); delay(10); return; }
  if (!wifiReported) {
    Serial.printf("Wi-Fi conectado. IP: %s\n", WiFi.localIP().toString().c_str());
    wifiReported = true;
  }
  color(CRGB::Green);
  if (click) {
    color(CRGB::Yellow);
    recording = SPIFFS.open("/recording.wav", "w");
    uint8_t h[44]; header(h, 0);
    if (!recording || recording.write(h, sizeof(h)) != sizeof(h) || !audioMode(true)) {
      Serial.println("Falha ao iniciar gravacao: arquivo ou microfone I2S.");
      recording.close(); stopAudio(); color(CRGB::Red); delay(1500); return;
    }
    recorded = 0;
    recordingNow = true;
    Serial.println("Gravacao iniciada. Clique novamente para enviar.");
  }
  delay(5);
}
