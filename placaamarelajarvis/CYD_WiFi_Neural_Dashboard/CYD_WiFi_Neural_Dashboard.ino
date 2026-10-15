#include <Arduino.h>
#include <Preferences.h>
#include <SPI.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#define ENABLE_SD_LOG 0
#if ENABLE_SD_LOG
#include <SD.h>
#endif

#define ILI9341_BLACK 0x0000
#define ILI9341_WHITE 0xFFFF

#ifndef DEEPSEEK_API_KEY
#define DEEPSEEK_API_KEY ""
#endif

#define WIFI_SSID ""
#define WIFI_PASS ""
#define FORCE_TOUCH_CALIBRATION false
#define TOUCH_CAL_VERSION 4

constexpr uint8_t TFT_CS = 15;
constexpr uint8_t TFT_DC = 2;
constexpr uint8_t TFT_SCLK = 14;
constexpr uint8_t TFT_MOSI = 13;
constexpr uint8_t TFT_MISO = 12;
constexpr uint8_t TFT_BL = 21;
constexpr uint8_t TOUCH_CS = 33;
constexpr uint8_t TOUCH_IRQ = 36;
constexpr uint8_t TOUCH_SCLK = 25;
constexpr uint8_t TOUCH_MOSI = 32;
constexpr uint8_t TOUCH_MISO = 39;
constexpr uint8_t SD_CS = 5;
constexpr uint8_t SD_SCLK = 18;
constexpr uint8_t SD_MISO = 19;
constexpr uint8_t SD_MOSI = 23;

SPIClass tftSPI(HSPI);
SPIClass touchSPI(VSPI);
#if ENABLE_SD_LOG
SPIClass sdSPI(VSPI);
#endif

class TinyILI9341 : public Print {
  int16_t cursorX = 0;
  int16_t cursorY = 0;
  uint16_t textColor = ILI9341_WHITE;
  uint16_t textBg = 0;
  uint8_t textScale = 1;

  void command(uint8_t cmd) {
    digitalWrite(TFT_DC, LOW);
    digitalWrite(TFT_CS, LOW);
    tftSPI.transfer(cmd);
    digitalWrite(TFT_CS, HIGH);
  }

  void data(uint8_t value) {
    digitalWrite(TFT_DC, HIGH);
    digitalWrite(TFT_CS, LOW);
    tftSPI.transfer(value);
    digitalWrite(TFT_CS, HIGH);
  }

  void data16(uint16_t value) {
    tftSPI.transfer16(value);
  }

  uint16_t glyph(char c) {
    if (c >= 'a' && c <= 'z') c -= 32;
    switch (c) {
      case '0': return 0b111101101101111;
      case '1': return 0b010110010010111;
      case '2': return 0b111001111100111;
      case '3': return 0b111001111001111;
      case '4': return 0b101101111001001;
      case '5': return 0b111100111001111;
      case '6': return 0b111100111101111;
      case '7': return 0b111001010010010;
      case '8': return 0b111101111101111;
      case '9': return 0b111101111001111;
      case 'A': return 0b010101111101101;
      case 'B': return 0b110101110101110;
      case 'C': return 0b111100100100111;
      case 'D': return 0b110101101101110;
      case 'E': return 0b111100110100111;
      case 'F': return 0b111100110100100;
      case 'G': return 0b111100101101111;
      case 'H': return 0b101101111101101;
      case 'I': return 0b111010010010111;
      case 'J': return 0b001001001101111;
      case 'K': return 0b101101110101101;
      case 'L': return 0b100100100100111;
      case 'M': return 0b101111111101101;
      case 'N': return 0b101111111111101;
      case 'O': return 0b111101101101111;
      case 'P': return 0b111101111100100;
      case 'Q': return 0b111101101111001;
      case 'R': return 0b111101111110101;
      case 'S': return 0b111100111001111;
      case 'T': return 0b111010010010010;
      case 'U': return 0b101101101101111;
      case 'V': return 0b101101101101010;
      case 'W': return 0b101101111111101;
      case 'X': return 0b101101010101101;
      case 'Y': return 0b101101010010010;
      case 'Z': return 0b111001010100111;
      case '-': return 0b000000111000000;
      case '_': return 0b000000000000111;
      case '.': return 0b000000000000010;
      case ':': return 0b000010000010000;
      case '/': return 0b001001010100100;
      case '%': return 0b101001010100101;
      case '+': return 0b000010111010000;
      case ' ': return 0;
      default: return 0b111001010000010;
    }
  }

  void setAddr(uint16_t x, uint16_t y, uint16_t w, uint16_t h) {
    command(0x2A);
    data(x >> 8); data(x & 0xFF); data((x + w - 1) >> 8); data((x + w - 1) & 0xFF);
    command(0x2B);
    data(y >> 8); data(y & 0xFF); data((y + h - 1) >> 8); data((y + h - 1) & 0xFF);
    command(0x2C);
  }

public:
  void begin() {
    pinMode(TFT_CS, OUTPUT);
    pinMode(TFT_DC, OUTPUT);
    digitalWrite(TFT_CS, HIGH);
    command(0x01); delay(120);
    command(0x28);
    command(0x3A); data(0x55);
    command(0x36); data(0x28);
    command(0x11); delay(120);
    command(0x29);
  }

  int16_t width() const { return 320; }
  int16_t height() const { return 240; }
  void setRotation(uint8_t) { command(0x36); data(0x28); }
  void setCursor(int16_t x, int16_t y) { cursorX = x; cursorY = y; }
  void setTextSize(uint8_t s) { textScale = max<uint8_t>(1, s); }
  void setTextColor(uint16_t c, uint16_t b) { textColor = c; textBg = b; }

  void fillRect(int16_t x, int16_t y, int16_t w, int16_t h, uint16_t color) {
    if (x < 0) { w += x; x = 0; }
    if (y < 0) { h += y; y = 0; }
    if (x + w > width()) w = width() - x;
    if (y + h > height()) h = height() - y;
    if (w <= 0 || h <= 0) return;
    setAddr(x, y, w, h);
    digitalWrite(TFT_DC, HIGH);
    digitalWrite(TFT_CS, LOW);
    for (uint32_t i = 0; i < (uint32_t)w * h; i++) data16(color);
    digitalWrite(TFT_CS, HIGH);
  }

  void fillScreen(uint16_t color) { fillRect(0, 0, width(), height(), color); }
  void drawFastHLine(int16_t x, int16_t y, int16_t w, uint16_t c) { fillRect(x, y, w, 1, c); }
  void drawFastVLine(int16_t x, int16_t y, int16_t h, uint16_t c) { fillRect(x, y, 1, h, c); }
  void drawRect(int16_t x, int16_t y, int16_t w, int16_t h, uint16_t c) {
    drawFastHLine(x, y, w, c); drawFastHLine(x, y + h - 1, w, c);
    drawFastVLine(x, y, h, c); drawFastVLine(x + w - 1, y, h, c);
  }
  void fillRoundRect(int16_t x, int16_t y, int16_t w, int16_t h, int16_t, uint16_t c) { fillRect(x, y, w, h, c); }
  void drawLine(int x0, int y0, int x1, int y1, uint16_t c) {
    int dx = abs(x1 - x0), sx = x0 < x1 ? 1 : -1;
    int dy = -abs(y1 - y0), sy = y0 < y1 ? 1 : -1;
    int err = dx + dy;
    while (true) {
      fillRect(x0, y0, 1, 1, c);
      if (x0 == x1 && y0 == y1) break;
      int e2 = 2 * err;
      if (e2 >= dy) { err += dy; x0 += sx; }
      if (e2 <= dx) { err += dx; y0 += sy; }
    }
  }
  void fillCircle(int16_t x0, int16_t y0, int16_t r, uint16_t c) {
    for (int16_t y = -r; y <= r; y++) {
      for (int16_t x = -r; x <= r; x++) if (x * x + y * y <= r * r) fillRect(x0 + x, y0 + y, 1, 1, c);
    }
  }
  size_t write(uint8_t ch) override {
    if (ch >= 128) return 1;
    if (ch == '\n') { cursorY += 6 * textScale; cursorX = 0; return 1; }
    uint16_t bits = glyph((char)ch);
    fillRect(cursorX, cursorY, 4 * textScale, 6 * textScale, textBg);
    for (uint8_t row = 0; row < 5; row++) {
      for (uint8_t col = 0; col < 3; col++) {
        if (bits & (1 << (14 - (row * 3 + col)))) {
          fillRect(cursorX + col * textScale, cursorY + row * textScale, textScale, textScale, textColor);
        }
      }
    }
    cursorX += 4 * textScale;
    return 1;
  }
};

TinyILI9341 lcd;
WiFiServer inputServer(80);
Preferences prefs;

constexpr uint8_t LDR_PIN = 34;
constexpr uint8_t LED_R = 4;
constexpr uint8_t LED_G = 16;
constexpr uint8_t LED_B = 17;
constexpr uint16_t BG = 0x0841;
constexpr uint16_t PANEL = 0x10A2;
constexpr uint16_t CYAN = 0x5DFF;
constexpr uint16_t GREEN = 0x07E0;
constexpr uint16_t AMBER = 0xFDC0;
constexpr uint16_t PINK = 0xF81F;
constexpr uint16_t MUTED = 0x9CD3;

String wifiSsid;
String wifiPass;
String wifiSelectedSsid = "";
String wifiPassInput = "";
String wifiKeyGroup = "";
String portalName;
String aiAnswer = "ESCOLHA UMA OPCAO. A IA VAI RESPONDER COM INSIGHTS SOBRE WIFI, MEMORIA, SENSOR E STATUS DO DISPOSITIVO.";
String aiStatus = "PRONTO";
String lastQuestion = "SEM PERGUNTA AINDA";
String typedQuestion = "";
String lastKeyGroup = "";
uint8_t lastKeyIndex = 0;
uint8_t wifiKeyIndex = 0;
uint32_t lastKeyTime = 0;
uint32_t wifiKeyTime = 0;
String tgHumor = "";
String tgPhrase = "COMO VOCE ESTA AGORA?";
String tgOptions[3];
String tgUsedPhrases[4];
String tgLastChoice = "";
uint8_t tgOptionCount = 0;
uint8_t tgStep = 0;
uint8_t tgView = 0;
bool tgSafety = false;

enum SupportKind : uint8_t {
  SUPPORT_NONE,
  SUPPORT_HELP_NOW,
  SUPPORT_OVERLOAD,
  SUPPORT_MEETING,
  SUPPORT_THINKING,
  SUPPORT_IMPULSE,
  SUPPORT_ANXIETY,
  SUPPORT_LOW_MOOD,
  SUPPORT_LOW_ENERGY,
  SUPPORT_ORGANIZE,
  SUPPORT_SILENT,
  SUPPORT_COMPANY
};

enum CompanionView : uint8_t {
  COMP_HOME,
  COMP_RESUME,
  COMP_SAFETY,
  COMP_INTENSITY,
  COMP_CAPACITY,
  COMP_CONTEXT,
  COMP_ACTION,
  COMP_CHECKIN,
  COMP_CONTACT,
  COMP_EMERGENCY,
  COMP_PAUSED,
  COMP_CLOSE,
  COMP_SUMMARY
};

enum CycleState : uint8_t {
  CYCLE_CLOSED,
  CYCLE_ACTIVE,
  CYCLE_PAUSED,
  CYCLE_DISCREET,
  CYCLE_WAITING_HUMAN,
  CYCLE_STABLE
};

SupportKind supportKind = SUPPORT_NONE;
CompanionView companionView = COMP_HOME;
CompanionView previousCompanionView = COMP_HOME;
CycleState cycleState = CYCLE_CLOSED;
uint8_t homePage = 0;
uint8_t interventionLevel = 1;
uint8_t discomfortLevel = 0;
uint8_t actionStep = 0;
uint8_t contextStep = 0;
uint8_t guidanceLevel = 1;
uint8_t overloadPatternCount = 0;
bool silentMode = false;
bool profileLearningConsent = false;
bool predictionConsent = false;
bool cloudProfileConsent = false;
bool eraseConfirm = false;
String compromisedCapacity = "nao informado";
String currentLocation = "nao informado";
String accompanimentState = "nao informado";
String canLeaveState = "nao informado";
String immediateEvent = "nao informado";
String needsActionNow = "nao informado";
String cycleGoal = "";
String cycleLastAction = "";
String cycleResult = "";
String preferredName = "";
String profileAge = "";
String trustedName = "";
String trustedPhone = "";
String profileNeuro = "";
String relevantConditions = "";
String sensoryNotes = "";
String earlySignals = "";
String worseningSignals = "";
String knownTriggers = "";
String stressSituations = "";
String helpfulStrategies = "";
String harmfulStrategies = "";
String communicationPreference = "toques e texto curto";
String calmingPhrase = "";
String phrasesToAvoid = "";
String treatmentNotes = "";
String routineNotes = "";
String personalGoals = "";
String personalLimits = "";
uint8_t autonomyLevel = 2;
bool portalActive = false;
bool smartConfigActive = false;
bool aiBusy = false;
bool inputServerStarted = false;
bool touchWasDown = false;
bool wifiEntryMode = false;
bool sdReady = false;
bool profileDepression = false;
bool profileAutism = false;
bool profileTdah = false;
bool profileSensory = false;
bool profileSleep = false;
bool profileWork = false;
uint8_t screen = 2;
uint8_t moodDownStreak = 0;
uint8_t moodAnxiousStreak = 0;
uint8_t moodTiredStreak = 0;
uint32_t lastFrame = 0;
uint32_t lastScan = 0;
uint32_t lastTouch = 0;
uint32_t lastSdAttempt = 0;
uint32_t lastFullClear = 0;
uint32_t lastMetricUpdate = 0;
uint32_t frames = 0;
uint32_t fpsMark = 0;
uint16_t fps = 0;
int scanCount = -1;
float phase = 0.0f;
uint8_t previousScreen = 255;
uint16_t touchXMin = 300;
uint16_t touchXMax = 3900;
uint16_t touchYMin = 250;
uint16_t touchYMax = 3800;
uint8_t touchSwap = 1;
uint8_t touchInvertX = 0;
uint8_t touchInvertY = 1;

const char *screenNames[] = {"SYS", "WIFI", "APOIO", "PERFIL"};

void drawTextBox(int x, int y, int w, int h, const String &label, const String &value, uint16_t accent);
void drawKey(int x, int y, int w, int h, const String &label, uint16_t color);
void drawAiMetrics();
void drawAiAnswer();
void drawNeuralScreen();
void drawConfigScreen();
void scanWifi();
void handleTamagotchiTouch(uint16_t x, uint16_t y);

uint16_t extrapolateRawEdge(int32_t rawAtA, int32_t rawAtB, int32_t screenA, int32_t screenB, int32_t target) {
  int32_t raw = rawAtA + ((target - screenA) * (rawAtB - rawAtA)) / (screenB - screenA);
  return constrain(raw, 150, 3950);
}

char latin1ToAscii(uint8_t c) {
  switch (c) {
    case 0xC0: case 0xC1: case 0xC2: case 0xC3: case 0xC4: case 0xC5:
    case 0xE0: case 0xE1: case 0xE2: case 0xE3: case 0xE4: case 0xE5: return 'a';
    case 0xC7: case 0xE7: return 'c';
    case 0xC8: case 0xC9: case 0xCA: case 0xCB:
    case 0xE8: case 0xE9: case 0xEA: case 0xEB: return 'e';
    case 0xCC: case 0xCD: case 0xCE: case 0xCF:
    case 0xEC: case 0xED: case 0xEE: case 0xEF: return 'i';
    case 0xD1: case 0xF1: return 'n';
    case 0xD2: case 0xD3: case 0xD4: case 0xD5: case 0xD6:
    case 0xF2: case 0xF3: case 0xF4: case 0xF5: case 0xF6: return 'o';
    case 0xD9: case 0xDA: case 0xDB: case 0xDC:
    case 0xF9: case 0xFA: case 0xFB: case 0xFC: return 'u';
    default: return 0;
  }
}

String asciiText(const String &in) {
  String out;
  out.reserve(in.length());
  for (uint16_t i = 0; i < in.length(); i++) {
    uint8_t c = (uint8_t)in[i];
    if (c == '\\' && i + 5 < in.length() && in[i + 1] == 'u' && in[i + 2] == '0' && in[i + 3] == '0') {
      char h1 = in[i + 4], h2 = in[i + 5];
      uint8_t v = 0;
      if (h1 >= '0' && h1 <= '9') v = (h1 - '0') << 4;
      else if (h1 >= 'A' && h1 <= 'F') v = (h1 - 'A' + 10) << 4;
      else if (h1 >= 'a' && h1 <= 'f') v = (h1 - 'a' + 10) << 4;
      if (h2 >= '0' && h2 <= '9') v |= h2 - '0';
      else if (h2 >= 'A' && h2 <= 'F') v |= h2 - 'A' + 10;
      else if (h2 >= 'a' && h2 <= 'f') v |= h2 - 'a' + 10;
      char m = latin1ToAscii(v);
      out += m ? m : '?';
      i += 5;
    } else if (c == 0xC3 && i + 1 < in.length()) {
      char m = latin1ToAscii((uint8_t)in[++i]);
      if (m) out += m;
    } else if (c < 128) {
      out += (char)c;
    }
  }
  return out;
}

void setStatusLed(uint8_t r, uint8_t g, uint8_t b) {
  digitalWrite(LED_R, r > 20 ? LOW : HIGH);
  digitalWrite(LED_G, g > 20 ? LOW : HIGH);
  digitalWrite(LED_B, b > 20 ? LOW : HIGH);
}

void drawText(int x, int y, const String &text, uint16_t color, uint8_t size = 1) {
  lcd.setTextColor(color, BG);
  lcd.setTextSize(size);
  lcd.setCursor(x, y);
  lcd.print(asciiText(text));
}

bool readTouchRaw(uint16_t &rawX, uint16_t &rawY) {
  digitalWrite(TOUCH_CS, LOW);
  touchSPI.transfer(0xD0);
  rawX = touchSPI.transfer16(0) >> 3;
  touchSPI.transfer(0x90);
  rawY = touchSPI.transfer16(0) >> 3;
  digitalWrite(TOUCH_CS, HIGH);
  return rawX > 150 && rawX < 3950 && rawY > 150 && rawY < 3950;
}

bool readTouchPoint(uint16_t &x, uint16_t &y) {
  uint16_t rawX, rawY;
  if (!readTouchRaw(rawX, rawY)) return false;
  uint16_t a = touchSwap ? rawY : rawX;
  uint16_t b = touchSwap ? rawX : rawY;
  int mappedX = map(a, touchXMin, touchXMax, 0, lcd.width() - 1);
  int mappedY = map(b, touchYMin, touchYMax, 0, lcd.height() - 1);
  if (touchInvertX) mappedX = (lcd.width() - 1) - mappedX;
  if (touchInvertY) mappedY = (lcd.height() - 1) - mappedY;
  x = constrain(mappedX, 0, lcd.width() - 1);
  y = constrain(mappedY, 0, lcd.height() - 1);
  Serial.print("TOUCH: raw=");
  Serial.print(rawX);
  Serial.print(",");
  Serial.print(rawY);
  Serial.print(" xy=");
  Serial.print(x);
  Serial.print(",");
  Serial.println(y);
  return true;
}

void loadTouchCalibration() {
  prefs.begin("touch", true);
  touchXMin = prefs.getUShort("xmin", touchXMin);
  touchXMax = prefs.getUShort("xmax", touchXMax);
  touchYMin = prefs.getUShort("ymin", touchYMin);
  touchYMax = prefs.getUShort("ymax", touchYMax);
  touchSwap = prefs.getUChar("swap", touchSwap);
  touchInvertX = prefs.getUChar("invx", touchInvertX);
  touchInvertY = prefs.getUChar("invy", touchInvertY);
  prefs.end();
}

void saveTouchCalibration() {
  prefs.begin("touch", false);
  prefs.putUShort("xmin", touchXMin);
  prefs.putUShort("xmax", touchXMax);
  prefs.putUShort("ymin", touchYMin);
  prefs.putUShort("ymax", touchYMax);
  prefs.putUChar("swap", touchSwap);
  prefs.putUChar("invx", touchInvertX);
  prefs.putUChar("invy", touchInvertY);
  prefs.end();
}

void drawCross(int x, int y, uint16_t color) {
  lcd.drawFastHLine(x - 12, y, 25, color);
  lcd.drawFastVLine(x, y - 12, 25, color);
  lcd.drawRect(x - 7, y - 7, 15, 15, color);
}

void waitRelease() {
  uint16_t rx, ry;
  while (readTouchRaw(rx, ry)) delay(30);
}

void runTouchCalibration() {
  const int sx[3] = {24, 296, 160};
  const int sy[3] = {24, 216, 120};
  uint16_t rx[3], ry[3];

  for (int i = 0; i < 3; i++) {
    lcd.fillScreen(BG);
    drawText(28, 88, "CALIBRAR TOUCH", CYAN, 2);
    drawText(22, 116, "TOQUE NO ALVO", ILI9341_WHITE, 1);
    drawCross(sx[i], sy[i], AMBER);
    bool got = false;
    while (!got) {
      uint16_t rawX, rawY;
      if (readTouchRaw(rawX, rawY)) {
        delay(80);
        uint32_t sumX = 0;
        uint32_t sumY = 0;
        int samples = 0;
        for (int s = 0; s < 10; s++) {
          uint16_t tx, ty;
          if (readTouchRaw(tx, ty)) {
            sumX += tx;
            sumY += ty;
            samples++;
          }
          delay(15);
        }
        if (samples >= 4) {
          rx[i] = sumX / samples;
          ry[i] = sumY / samples;
          got = true;
          waitRelease();
        }
      }
      delay(20);
    }
  }

  touchSwap = abs((int)ry[1] - (int)ry[0]) > abs((int)rx[1] - (int)rx[0]);
  uint16_t ax0 = touchSwap ? ry[0] : rx[0];
  uint16_t ax1 = touchSwap ? ry[1] : rx[1];
  uint16_t ay0 = touchSwap ? rx[0] : ry[0];
  uint16_t ay1 = touchSwap ? rx[1] : ry[1];
  touchInvertX = ax0 > ax1;
  touchInvertY = ay0 > ay1;
  uint16_t rawX0 = extrapolateRawEdge(ax0, ax1, sx[0], sx[1], 0);
  uint16_t rawX1 = extrapolateRawEdge(ax0, ax1, sx[0], sx[1], lcd.width() - 1);
  uint16_t rawY0 = extrapolateRawEdge(ay0, ay1, sy[0], sy[1], 0);
  uint16_t rawY1 = extrapolateRawEdge(ay0, ay1, sy[0], sy[1], lcd.height() - 1);
  touchXMin = min(rawX0, rawX1);
  touchXMax = max(rawX0, rawX1);
  touchYMin = min(rawY0, rawY1);
  touchYMax = max(rawY0, rawY1);
  saveTouchCalibration();

  lcd.fillScreen(BG);
  drawText(36, 100, "TOUCH OK", GREEN, 2);
  delay(800);
}

void drawWrapped(int x, int y, int w, int h, const String &text, uint16_t color, uint16_t bg, uint8_t size = 1) {
  lcd.fillRect(x, y, w, h, bg);
  lcd.setTextColor(color, bg);
  lcd.setTextSize(size);
  int charsPerLine = max(1, w / (4 * size));
  int lineH = 7 * size;
  int line = 0;
  String word;
  String out;
  String clean = asciiText(text);
  for (uint16_t i = 0; i <= clean.length(); i++) {
    char c = i < clean.length() ? clean[i] : ' ';
    if (c == '\n' || c == ' ' || i == text.length()) {
      if (out.length() + word.length() + 1 > charsPerLine) {
        lcd.setCursor(x, y + line * lineH);
        lcd.print(out);
        line++;
        out = "";
        if (y + (line + 1) * lineH > y + h) return;
      }
      if (out.length()) out += " ";
      out += word;
      word = "";
      if (c == '\n') {
        lcd.setCursor(x, y + line * lineH);
        lcd.print(out);
        line++;
        out = "";
        if (y + (line + 1) * lineH > y + h) return;
      }
    } else {
      word += c;
    }
  }
  if (out.length() && y + line * lineH < y + h) {
    lcd.setCursor(x, y + line * lineH);
    lcd.print(out);
  }
}

void card(int x, int y, int w, int h, const String &label, uint16_t accent) {
  lcd.fillRoundRect(x, y, w, h, 6, PANEL);
  lcd.drawFastHLine(x + 8, y + 22, w - 16, accent);
  lcd.setTextColor(MUTED, PANEL);
  lcd.setTextSize(1);
  lcd.setCursor(x + 8, y + 8);
  lcd.print(label);
}

void valueCard(int x, int y, int w, int h, const String &label, const String &value, uint16_t accent) {
  card(x, y, w, h, label, accent);
  lcd.setTextColor(ILI9341_WHITE, PANEL);
  lcd.setTextSize(2);
  lcd.setCursor(x + 8, y + 34);
  lcd.print(value);
}

void drawNav() {
  int w = lcd.width() / 4;
  for (int i = 0; i < 4; i++) {
    uint16_t c = i == screen ? CYAN : 0x2945;
    lcd.fillRect(i * w, lcd.height() - 34, w - 1, 34, i == screen ? 0x19A7 : PANEL);
    lcd.setTextColor(i == screen ? ILI9341_BLACK : ILI9341_WHITE, i == screen ? 0x19A7 : PANEL);
    lcd.setTextSize(1);
    lcd.setCursor(i * w + 18, lcd.height() - 22);
    lcd.print(screenNames[i]);
    lcd.drawFastHLine(i * w, lcd.height() - 34, w - 1, c);
  }
}

void drawTopNav() {
  int w = lcd.width() / 4;
  for (int i = 0; i < 4; i++) {
    uint16_t bg = i == screen ? 0x19A7 : 0x0028;
    lcd.fillRect(i * w, 0, w - 1, 26, bg);
    lcd.setTextColor(i == screen ? ILI9341_BLACK : ILI9341_WHITE, bg);
    lcd.setTextSize(1);
    lcd.setCursor(i * w + 18, 10);
    lcd.print(screenNames[i]);
  }
}

String ipText() {
  return WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString() : "SMARTCFG";
}

int wifiQuality() {
  if (WiFi.status() != WL_CONNECTED) return 0;
  int rssi = WiFi.RSSI();
  return constrain(map(rssi, -95, -35, 0, 100), 0, 100);
}

String maskedPass() {
  String out;
  for (uint16_t i = 0; i < wifiPassInput.length() && i < 18; i++) out += '*';
  return out.length() ? out : "...";
}

void loadProfile() {
  prefs.begin("profile", true);
  profileDepression = prefs.getBool("dep", false);
  profileAutism = prefs.getBool("aut", false);
  profileTdah = prefs.getBool("tdah", false);
  profileSensory = prefs.getBool("sens", false);
  profileSleep = prefs.getBool("sleep", false);
  profileWork = prefs.getBool("work", false);
  moodDownStreak = prefs.getUChar("down", 0);
  moodAnxiousStreak = prefs.getUChar("anx", 0);
  moodTiredStreak = prefs.getUChar("tired", 0);
  preferredName = prefs.getString("name", "");
  profileAge = prefs.getString("age", "");
  trustedName = prefs.getString("trust_name", "");
  trustedPhone = prefs.getString("trust_phone", "");
  profileNeuro = prefs.getString("neuro", "");
  relevantConditions = prefs.getString("conditions", "");
  sensoryNotes = prefs.getString("sensory", "");
  earlySignals = prefs.getString("early", "");
  worseningSignals = prefs.getString("worse", "");
  knownTriggers = prefs.getString("triggers", "");
  stressSituations = prefs.getString("stress", "");
  helpfulStrategies = prefs.getString("helps", "");
  harmfulStrategies = prefs.getString("harms", "");
  communicationPreference = prefs.getString("comm", "toques e texto curto");
  calmingPhrase = prefs.getString("calm", "");
  phrasesToAvoid = prefs.getString("avoid", "");
  treatmentNotes = prefs.getString("treatment", "");
  routineNotes = prefs.getString("routine", "");
  personalGoals = prefs.getString("goals", "");
  personalLimits = prefs.getString("limits", "");
  autonomyLevel = constrain((int)prefs.getUChar("autonomy", 2), 1, 3);
  guidanceLevel = constrain((int)prefs.getUChar("guidance", 1), 0, 2);
  profileLearningConsent = prefs.getBool("learn_ok", false);
  predictionConsent = prefs.getBool("predict_ok", false);
  cloudProfileConsent = prefs.getBool("cloud_ok", false);
  overloadPatternCount = prefs.getUChar("overloads", 0);
  prefs.end();
}

void saveProfile() {
  prefs.begin("profile", false);
  prefs.putBool("dep", profileDepression);
  prefs.putBool("aut", profileAutism);
  prefs.putBool("tdah", profileTdah);
  prefs.putBool("sens", profileSensory);
  prefs.putBool("sleep", profileSleep);
  prefs.putBool("work", profileWork);
  prefs.putUChar("down", moodDownStreak);
  prefs.putUChar("anx", moodAnxiousStreak);
  prefs.putUChar("tired", moodTiredStreak);
  prefs.putString("name", preferredName);
  prefs.putString("age", profileAge);
  prefs.putString("trust_name", trustedName);
  prefs.putString("trust_phone", trustedPhone);
  prefs.putString("neuro", profileNeuro);
  prefs.putString("conditions", relevantConditions);
  prefs.putString("sensory", sensoryNotes);
  prefs.putString("early", earlySignals);
  prefs.putString("worse", worseningSignals);
  prefs.putString("triggers", knownTriggers);
  prefs.putString("stress", stressSituations);
  prefs.putString("helps", helpfulStrategies);
  prefs.putString("harms", harmfulStrategies);
  prefs.putString("comm", communicationPreference);
  prefs.putString("calm", calmingPhrase);
  prefs.putString("avoid", phrasesToAvoid);
  prefs.putString("treatment", treatmentNotes);
  prefs.putString("routine", routineNotes);
  prefs.putString("goals", personalGoals);
  prefs.putString("limits", personalLimits);
  prefs.putUChar("autonomy", autonomyLevel);
  prefs.putUChar("guidance", guidanceLevel);
  prefs.putBool("learn_ok", profileLearningConsent);
  prefs.putBool("predict_ok", predictionConsent);
  prefs.putBool("cloud_ok", cloudProfileConsent);
  prefs.putUChar("overloads", overloadPatternCount);
  prefs.end();
}

void loadCycle() {
  prefs.begin("cycle", true);
  cycleState = (CycleState)constrain((int)prefs.getUChar("state", CYCLE_CLOSED), (int)CYCLE_CLOSED, (int)CYCLE_STABLE);
  supportKind = (SupportKind)constrain((int)prefs.getUChar("kind", SUPPORT_NONE), (int)SUPPORT_NONE, (int)SUPPORT_COMPANY);
  interventionLevel = constrain((int)prefs.getUChar("level", 1), 1, 4);
  discomfortLevel = constrain((int)prefs.getUChar("discomfort", 0), 0, 5);
  actionStep = constrain((int)prefs.getUChar("action", 0), 0, 2);
  contextStep = constrain((int)prefs.getUChar("context_step", 0), 0, 4);
  silentMode = prefs.getBool("silent", false);
  compromisedCapacity = prefs.getString("capacity", "nao informado");
  currentLocation = prefs.getString("location", "nao informado");
  accompanimentState = prefs.getString("company", "nao informado");
  canLeaveState = prefs.getString("can_leave", "nao informado");
  immediateEvent = prefs.getString("event_before", "nao informado");
  needsActionNow = prefs.getString("act_now", "nao informado");
  cycleGoal = prefs.getString("goal", "");
  cycleLastAction = prefs.getString("last_action", "");
  cycleResult = prefs.getString("result", "");
  prefs.end();
  companionView = cycleState == CYCLE_CLOSED ? COMP_HOME : COMP_RESUME;
}

void saveCycle() {
  prefs.begin("cycle", false);
  prefs.putUChar("state", cycleState);
  prefs.putUChar("kind", supportKind);
  prefs.putUChar("level", interventionLevel);
  prefs.putUChar("discomfort", discomfortLevel);
  prefs.putUChar("action", actionStep);
  prefs.putUChar("context_step", contextStep);
  prefs.putBool("silent", silentMode);
  prefs.putString("capacity", compromisedCapacity);
  prefs.putString("location", currentLocation);
  prefs.putString("company", accompanimentState);
  prefs.putString("can_leave", canLeaveState);
  prefs.putString("event_before", immediateEvent);
  prefs.putString("act_now", needsActionNow);
  prefs.putString("goal", cycleGoal);
  prefs.putString("last_action", cycleLastAction);
  prefs.putString("result", cycleResult);
  prefs.end();
}

void clearCycle() {
  cycleState = CYCLE_CLOSED;
  supportKind = SUPPORT_NONE;
  interventionLevel = 1;
  discomfortLevel = 0;
  actionStep = 0;
  contextStep = 0;
  silentMode = false;
  compromisedCapacity = "nao informado";
  currentLocation = "nao informado";
  accompanimentState = "nao informado";
  canLeaveState = "nao informado";
  immediateEvent = "nao informado";
  needsActionNow = "nao informado";
  cycleGoal = "";
  cycleLastAction = "";
  cycleResult = "";
  prefs.begin("cycle", false);
  prefs.clear();
  prefs.end();
}

String profileFlagsJson() {
  if (!cloudProfileConsent) return "{\consentimento_perfil\:false}";
  String p = "{";
  p += "\consentimento_perfil\:true,";
  p += "\"depressao\":" + String(profileDepression ? "true" : "false") + ",";
  p += "\"autismo\":" + String(profileAutism ? "true" : "false") + ",";
  p += "\"tdah\":" + String(profileTdah ? "true" : "false") + ",";
  p += "\"sensibilidade_sensorial\":" + String(profileSensory ? "true" : "false") + ",";
  p += "\"sono\":" + String(profileSleep ? "true" : "false") + ",";
  p += "\"trabalho\":" + String(profileWork ? "true" : "false") + "}";
  return p;
}

String trendJson() {
  return "{\"pra_baixo\":" + String(moodDownStreak) + ",\"ansioso\":" + String(moodAnxiousStreak) + ",\"cansado\":" + String(moodTiredStreak) + "}";
}

String profileSummary() {
  String s = "";
  if (profileDepression) s += "DEP ";
  if (profileAutism) s += "AUT ";
  if (profileTdah) s += "TDAH ";
  if (profileSensory) s += "SENS ";
  if (profileSleep) s += "SONO ";
  if (profileWork) s += "TRAB ";
  return s.length() ? s : "PADRAO";
}

void updateMoodTrend(const String &humor) {
  moodDownStreak = humor == "pra baixo" ? min<uint8_t>(moodDownStreak + 1, 9) : 0;
  moodAnxiousStreak = humor == "ansioso" ? min<uint8_t>(moodAnxiousStreak + 1, 9) : 0;
  moodTiredStreak = humor == "cansado" ? min<uint8_t>(moodTiredStreak + 1, 9) : 0;
  saveProfile();
}

void drawHeader(const String &title) {
  drawTopNav();
  lcd.fillRect(0, 28, lcd.width(), 28, BG);
  lcd.setTextColor(CYAN, BG);
  lcd.setTextSize(2);
  lcd.setCursor(8, 36);
  lcd.print(title);
  lcd.setTextSize(1);
  lcd.setTextColor(WiFi.status() == WL_CONNECTED ? GREEN : AMBER, BG);
  lcd.setCursor(lcd.width() - 82, 39);
  lcd.print(WiFi.status() == WL_CONNECTED ? "ONLINE" : "CONFIG");
}

void drawOverview() {
  drawHeader("CYD CORE");
  int lightValue = analogRead(LDR_PIN);
  int lightPct = constrain(map(lightValue, 0, 4095, 0, 100), 0, 100);
  int heapKb = ESP.getFreeHeap() / 1024;
  int cpuLoad = constrain((int)(42 + sinf(phase) * 22 + (100 - wifiQuality()) / 6), 3, 96);

  valueCard(8, 66, 104, 54, "WIFI", String(wifiQuality()) + "%", CYAN);
  valueCard(128, 66, 104, 54, "LUZ", String(lightPct) + "%", AMBER);
  valueCard(8, 130, 104, 54, "HEAP", String(heapKb) + "K", GREEN);
  valueCard(128, 130, 104, 54, "CPU", String(cpuLoad) + "%", PINK);

  card(8, 194, 224, 38, "REDE", CYAN);
  lcd.setTextColor(ILI9341_WHITE, PANEL);
  lcd.setTextSize(1);
  lcd.setCursor(18, 214);
  lcd.print(WiFi.status() == WL_CONNECTED ? WiFi.SSID() : "SMARTCONFIG");

  int barW = map(cpuLoad, 0, 100, 0, 196);
  lcd.drawRect(18, 226, 196, 8, 0x632C);
  lcd.fillRect(19, 227, barW, 6, PINK);
}

void drawWifiScreen() {
  drawHeader("WIFI RADAR");
  if (wifiEntryMode) {
    drawTextBox(8, 64, 224, 40, "REDE", wifiSelectedSsid, CYAN);
    drawTextBox(8, 112, 224, 36, "SENHA", maskedPass(), AMBER);
    lcd.fillRect(6, 154, 228, 80, BG);
    drawKey(8, 154, 70, 18, "1ABC", CYAN);
    drawKey(85, 154, 70, 18, "2DEF", CYAN);
    drawKey(162, 154, 70, 18, "3GHI", CYAN);
    drawKey(8, 176, 70, 18, "4JKL", GREEN);
    drawKey(85, 176, 70, 18, "5MNO", GREEN);
    drawKey(162, 176, 70, 18, "6PQRS", GREEN);
    drawKey(8, 198, 70, 18, "7TUV", AMBER);
    drawKey(85, 198, 70, 18, "8WXYZ", AMBER);
    drawKey(162, 198, 70, 18, "9.-_", AMBER);
    drawKey(8, 220, 70, 18, "DEL", 0xD6BA);
    drawKey(85, 220, 70, 18, "0", 0x7BEF);
    drawKey(162, 220, 70, 18, "OK", PINK);
    return;
  }
  card(8, 66, 224, 48, "CONEXAO", CYAN);
  lcd.setTextColor(ILI9341_WHITE, PANEL);
  lcd.setTextSize(1);
  lcd.setCursor(18, 90);
  lcd.print(asciiText(WiFi.status() == WL_CONNECTED ? WiFi.SSID() : "TOQUE PARA CONFIG"));
  lcd.setCursor(18, 104);
  lcd.print(ipText());

  lcd.setTextColor(MUTED, BG);
  lcd.setCursor(8, 120);
  lcd.print("Redes proximas");

  if (scanCount < 0) {
    drawText(24, 142, "toque em WIFI para scan", AMBER);
    return;
  }

  int rows = min(scanCount, 5);
  for (int i = 0; i < rows; i++) {
    int y = 126 + i * 21;
    int q = constrain(map(WiFi.RSSI(i), -95, -35, 0, 100), 0, 100);
    lcd.fillRect(8, y, 224, 18, i % 2 ? 0x1082 : 0x18C3);
    lcd.setTextColor(ILI9341_WHITE, i % 2 ? 0x1082 : 0x18C3);
    lcd.setCursor(12, y + 5);
    String name = WiFi.SSID(i);
    if (name.length() > 16) name = name.substring(0, 16);
    lcd.print(asciiText(name));
    lcd.drawRect(142, y + 5, 72, 8, 0x632C);
    lcd.fillRect(143, y + 6, map(q, 0, 100, 0, 70), 6, q > 60 ? GREEN : AMBER);
  }
}

String jsonEscape(const String &in) {
  String out;
  out.reserve(in.length() + 16);
  for (uint16_t i = 0; i < in.length(); i++) {
    char c = in[i];
    if (c == '"' || c == '\\') {
      out += '\\';
      out += c;
    } else if (c == '\n') {
      out += "\\n";
    } else if ((uint8_t)c >= 32) {
      out += c;
    }
  }
  return out;
}

void restoreTouchBus() {
  touchSPI.begin(TOUCH_SCLK, TOUCH_MISO, TOUCH_MOSI, TOUCH_CS);
  digitalWrite(TOUCH_CS, HIGH);
}

bool tryInitSd() {
#if ENABLE_SD_LOG
  if (millis() - lastSdAttempt < 8000 && lastSdAttempt != 0) return sdReady;
  lastSdAttempt = millis();
  pinMode(SD_CS, OUTPUT);
  digitalWrite(SD_CS, HIGH);
  sdSPI.begin(SD_SCLK, SD_MISO, SD_MOSI, SD_CS);
  sdReady = SD.begin(SD_CS, sdSPI, 4000000);
  if (sdReady && !SD.exists("/tamagotchi_log.jsonl")) {
    File f = SD.open("/tamagotchi_log.jsonl", FILE_WRITE);
    if (f) {
      f.println("{\"event\":\"log_start\"}");
      f.close();
    }
  }
  restoreTouchBus();
  return sdReady;
#else
  sdReady = false;
  return false;
#endif
}

void logSdLine(const String &line) {
#if ENABLE_SD_LOG
  if (!sdReady && !tryInitSd()) return;
  sdSPI.begin(SD_SCLK, SD_MISO, SD_MOSI, SD_CS);
  if (!SD.begin(SD_CS, sdSPI, 4000000)) {
    sdReady = false;
    restoreTouchBus();
    return;
  }
  File f = SD.open("/tamagotchi_log.jsonl", FILE_APPEND);
  if (f) {
    f.println(line);
    f.close();
  }
  restoreTouchBus();
#else
  (void)line;
#endif
}

void logInteraction(const String &eventName, const String &detail) {
  String line = "{\"event\":\"" + jsonEscape(eventName) + "\",";
  line += "\"humor\":\"" + jsonEscape(tgHumor) + "\",";
  line += "\"etapa\":" + String(tgStep) + ",";
  line += "\"detalhe\":\"" + jsonEscape(detail) + "\"}";
  logSdLine(line);
}

String htmlEscape(const String &in) {
  String out;
  for (uint16_t i = 0; i < in.length(); i++) {
    char c = in[i];
    if (c == '<') out += "&lt;";
    else if (c == '>') out += "&gt;";
    else if (c == '&') out += "&amp;";
    else if (c == '"') out += "&quot;";
    else if (c == '\'') out += "&#39;";
    else out += c;
  }
  return out;
}

String urlDecode(const String &in) {
  String out;
  for (uint16_t i = 0; i < in.length(); i++) {
    char c = in[i];
    if (c == '+') out += ' ';
    else if (c == '%' && i + 2 < in.length()) {
      char h1 = in[i + 1];
      char h2 = in[i + 2];
      uint8_t v = 0;
      if (h1 >= '0' && h1 <= '9') v = (h1 - '0') << 4;
      else if (h1 >= 'A' && h1 <= 'F') v = (h1 - 'A' + 10) << 4;
      else if (h1 >= 'a' && h1 <= 'f') v = (h1 - 'a' + 10) << 4;
      if (h2 >= '0' && h2 <= '9') v |= h2 - '0';
      else if (h2 >= 'A' && h2 <= 'F') v |= h2 - 'A' + 10;
      else if (h2 >= 'a' && h2 <= 'f') v |= h2 - 'a' + 10;
      out += (char)v;
      i += 2;
    } else {
      out += c;
    }
  }
  return out;
}

String jsonUnescape(const String &in) {
  String out;
  out.reserve(in.length());
  for (uint16_t i = 0; i < in.length(); i++) {
    char c = in[i];
    if (c == '\\' && i + 1 < in.length()) {
      char n = in[++i];
      if (n == 'u' && i + 4 < in.length()) {
        String esc = "\\u";
        esc += in.substring(i + 1, i + 5);
        out += asciiText(esc);
        i += 4;
      } else if (n == 'n') out += ' ';
      else if (n == 'r') out += ' ';
      else if (n == 't') out += ' ';
      else out += n;
    } else {
      out += c;
    }
  }
  return out;
}

String extractDeepSeekContent(const String &response) {
  int p = response.indexOf("\"content\":\"");
  if (p < 0) return "NAO CONSEGUI LER A RESPOSTA DA API.";
  p += 11;
  String raw;
  bool esc = false;
  for (int i = p; i < response.length(); i++) {
    char c = response[i];
    if (esc) {
      raw += '\\';
      raw += c;
      esc = false;
      continue;
    }
    if (c == '\\') {
      esc = true;
      continue;
    }
    if (c == '"') break;
    raw += c;
  }
  return jsonUnescape(raw);
}

String localAnswer(const String &topic) {
  int lightPct = constrain(map(analogRead(LDR_PIN), 0, 4095, 0, 100), 0, 100);
  int heapKb = ESP.getFreeHeap() / 1024;
  if (topic == "server") return "SERVIDOR: WIFI " + String(wifiQuality()) + "%, HEAP " + String(heapKb) + "K. SE A API FALHAR, CONFIRA INTERNET E CREDITOS.";
  if (topic == "status") return "STATUS: IP " + ipText() + ", LUZ " + String(lightPct) + "%, MEMORIA LIVRE " + String(heapKb) + "K.";
  if (topic == "wifi") return "WIFI: SINAL " + String(wifiQuality()) + "%. SE FICAR ABAIXO DE 45%, APROXIME DO ROTEADOR.";
  return "INSIGHT: USE ESTA TELA COMO COCKPIT. TOQUE EM STATUS, SERVIDOR OU WIFI PARA TER UMA LEITURA UTIL.";
}

String askDeepSeek(const String &topic, const String &prompt) {
  if (WiFi.status() != WL_CONNECTED) return "SEM WIFI. USE SMARTCONFIG NA TELA CFG.";
  if (String(DEEPSEEK_API_KEY).length() < 10) return localAnswer(topic);

  WiFiClientSecure client;
  client.setInsecure();
  client.setTimeout(20000);
  if (!client.connect("api.deepseek.com", 443)) return "FALHA TLS COM API.DEEPSEEK.COM.";

  String sys = "Responda em portugues do Brasil sem acentos, muito curto, util, sem markdown. Maximo 280 caracteres.";
  String body = "{\"model\":\"deepseek-v4-flash\",\"messages\":[";
  body += "{\"role\":\"system\",\"content\":\"" + jsonEscape(sys) + "\"},";
  body += "{\"role\":\"user\",\"content\":\"" + jsonEscape(prompt) + "\"}],";
  body += "\"thinking\":{\"type\":\"disabled\"},\"max_tokens\":120,\"stream\":false}";

  client.print("POST /chat/completions HTTP/1.1\r\n");
  client.print("Host: api.deepseek.com\r\n");
  client.print("Content-Type: application/json\r\n");
  client.print("Authorization: Bearer ");
  client.print(DEEPSEEK_API_KEY);
  client.print("\r\nContent-Length: ");
  client.print(body.length());
  client.print("\r\nConnection: close\r\n\r\n");
  client.print(body);

  String response;
  uint32_t deadline = millis() + 25000;
  while (millis() < deadline && (client.connected() || client.available())) {
    while (client.available()) {
      char c = client.read();
      if (response.length() < 14000) response += c;
    }
    delay(5);
  }
  if (response.indexOf(" 200 ") < 0) return "API RETORNOU ERRO. CONFIRA CHAVE, CREDITOS E INTERNET.";
  return extractDeepSeekContent(response);
}

void runAiPrompt(uint8_t id) {
  if (aiBusy) return;
  aiBusy = true;
  screen = 2;
  aiStatus = "PENSANDO";
  aiAnswer = "CHAMANDO IA...";
  drawAiMetrics();
  drawAiAnswer();
  drawNav();

  String topic = "insight";
  String prompt = "Gere um insight curto para um assistente em ESP32 com display touch, WiFi, memoria livre " + String(ESP.getFreeHeap() / 1024) + " KB e sensor de luz.";
  if (id == 1) {
    topic = "wifi";
    prompt = "Analise o WiFi desta placa ESP32: sinal " + String(wifiQuality()) + "%, IP " + ipText() + ". Diga se esta bom e uma acao pratica.";
  } else if (id == 2) {
    topic = "status";
    prompt = "Resuma o status da placa ESP32: memoria livre " + String(ESP.getFreeHeap() / 1024) + " KB, luz " + String(constrain(map(analogRead(LDR_PIN), 0, 4095, 0, 100), 0, 100)) + "%, WiFi " + String(wifiQuality()) + "%.";
  } else if (id == 3) {
    topic = "server";
    prompt = "De um diagnostico curto do servidor/API DeepSeek visto de uma ESP32: WiFi " + String(wifiQuality()) + "%, heap " + String(ESP.getFreeHeap() / 1024) + " KB. Foque em acao.";
  }
  aiAnswer = askDeepSeek(topic, prompt);
  aiStatus = String(DEEPSEEK_API_KEY).length() < 10 ? "LOCAL" : "DEEPSEEK";
  aiBusy = false;
  drawAiMetrics();
  drawAiAnswer();
}

void drawAiButton(int x, int y, int w, int h, const String &label, uint16_t color) {
  lcd.fillRoundRect(x, y, w, h, 4, color);
  lcd.setTextColor(ILI9341_BLACK, color);
  lcd.setTextSize(1);
  lcd.setCursor(x + 8, y + h / 2 - 2);
  lcd.print(label);
}

void drawTextBox(int x, int y, int w, int h, const String &label, const String &value, uint16_t accent) {
  lcd.fillRoundRect(x, y, w, h, 4, PANEL);
  int dividerY = y + min(18, max(10, h / 2));
  lcd.drawFastHLine(x + 6, dividerY, w - 12, accent);
  lcd.setTextColor(MUTED, PANEL);
  lcd.setTextSize(1);
  lcd.setCursor(x + 8, y + 6);
  lcd.print(label);
  int bodyY = dividerY + 5;
  int bodyH = max(8, y + h - bodyY - 3);
  drawWrapped(x + 8, bodyY, w - 16, bodyH, value.length() ? value : "...", ILI9341_WHITE, PANEL, 1);
}

void drawKey(int x, int y, int w, int h, const String &label, uint16_t color) {
  lcd.fillRoundRect(x, y, w, h, 3, color);
  lcd.setTextColor(ILI9341_BLACK, color);
  lcd.setTextSize(1);
  int tx = x + max(3, (w - (int)label.length() * 4) / 2);
  lcd.setCursor(tx, y + h / 2 - 2);
  lcd.print(label);
}

void drawQuestionField() {
  drawTextBox(8, 30, 224, 46, "PERGUNTA", typedQuestion, CYAN);
}

void drawAnswerField() {
  drawTextBox(8, 80, 224, 54, "RESPOSTA IA", aiAnswer, PINK);
  lcd.setTextColor(aiBusy ? AMBER : GREEN, PANEL);
  lcd.setTextSize(1);
  lcd.setCursor(176, 88);
  lcd.print(aiStatus);
}

void drawKeyboard() {
  lcd.fillRect(6, 140, 228, 96, BG);
  drawKey(8, 140, 70, 20, "ABC", CYAN);
  drawKey(85, 140, 70, 20, "DEF", CYAN);
  drawKey(162, 140, 70, 20, "GHI", CYAN);
  drawKey(8, 164, 70, 20, "JKL", GREEN);
  drawKey(85, 164, 70, 20, "MNO", GREEN);
  drawKey(162, 164, 70, 20, "PQRS", GREEN);
  drawKey(8, 188, 70, 20, "TUV", AMBER);
  drawKey(85, 188, 70, 20, "WXYZ", AMBER);
  drawKey(162, 188, 70, 20, "ESPACO", 0x7BEF);
  drawKey(8, 212, 70, 22, "DEL", 0xD6BA);
  drawKey(85, 212, 70, 22, "LIMPAR", 0xD6BA);
  drawKey(162, 212, 70, 22, "ENVIAR", PINK);
}

void drawAskScreen() {
  drawTopNav();
  drawQuestionField();
  drawAnswerField();
  drawKeyboard();
}

void askTypedQuestion() {
  if (aiBusy || typedQuestion.length() == 0) return;
  lastQuestion = typedQuestion;
  logSdLine("{\"event\":\"pergunta_ia\",\"texto\":\"" + jsonEscape(typedQuestion) + "\"}");
  aiBusy = true;
  aiStatus = "PENSANDO";
  aiAnswer = "ENVIANDO PARA A IA...";
  drawAnswerField();
  String prompt = "Responda em portugues do Brasil de forma clara e objetiva, maximo 500 caracteres. Pergunta: " + typedQuestion;
  aiAnswer = askDeepSeek("custom", prompt);
  logSdLine("{\"event\":\"resposta_ia\",\"texto\":\"" + jsonEscape(aiAnswer) + "\"}");
  aiStatus = String(DEEPSEEK_API_KEY).length() < 10 ? "LOCAL" : "DEEPSEEK";
  aiBusy = false;
  drawAnswerField();
}

void pressLetterGroup(const String &group) {
  if (typedQuestion.length() >= 120) return;
  uint32_t now = millis();
  if (lastKeyGroup == group && now - lastKeyTime < 900 && typedQuestion.length()) {
    lastKeyIndex = (lastKeyIndex + 1) % group.length();
    typedQuestion.setCharAt(typedQuestion.length() - 1, group[lastKeyIndex]);
  } else {
    lastKeyGroup = group;
    lastKeyIndex = 0;
    typedQuestion += group[0];
  }
  lastKeyTime = now;
}

void handleKeyboardTouch(uint16_t x, uint16_t y) {
  int col = -1;
  if (x >= 8 && x < 78) col = 0;
  else if (x >= 85 && x < 155) col = 1;
  else if (x >= 162 && x < 232) col = 2;
  if (col < 0) return;

  int row = -1;
  if (y >= 140 && y < 160) row = 0;
  else if (y >= 164 && y < 184) row = 1;
  else if (y >= 188 && y < 208) row = 2;
  else if (y >= 212 && y < 236) row = 3;
  if (row < 0) return;

  if (row == 0 && col == 0) pressLetterGroup("ABC");
  else if (row == 0 && col == 1) pressLetterGroup("DEF");
  else if (row == 0 && col == 2) pressLetterGroup("GHI");
  else if (row == 1 && col == 0) pressLetterGroup("JKL");
  else if (row == 1 && col == 1) pressLetterGroup("MNO");
  else if (row == 1 && col == 2) pressLetterGroup("PQRS");
  else if (row == 2 && col == 0) pressLetterGroup("TUV");
  else if (row == 2 && col == 1) pressLetterGroup("WXYZ");
  else if (row == 2 && col == 2 && typedQuestion.length() < 120) {
    typedQuestion += " ";
    lastKeyGroup = "";
  } else if (row == 3 && col == 0) {
    if (typedQuestion.length()) typedQuestion.remove(typedQuestion.length() - 1);
    lastKeyGroup = "";
  } else if (row == 3 && col == 1) {
    typedQuestion = "";
    lastKeyGroup = "";
  } else if (row == 3 && col == 2) {
    lastKeyGroup = "";
    askTypedQuestion();
  }
  drawQuestionField();
}

void drawAiMetrics() {
  int lightPct = constrain(map(analogRead(LDR_PIN), 0, 4095, 0, 100), 0, 100);
  int heapKb = ESP.getFreeHeap() / 1024;
  int q = wifiQuality();

  lcd.fillRect(82, 34, 150, 46, PANEL);
  lcd.setTextSize(1);
  lcd.setTextColor(CYAN, PANEL);
  lcd.setCursor(90, 44);
  lcd.print("WIFI ");
  lcd.setTextColor(ILI9341_WHITE, PANEL);
  lcd.print(q);
  lcd.print("%");

  lcd.setTextColor(GREEN, PANEL);
  lcd.setCursor(154, 44);
  lcd.print("MEM ");
  lcd.setTextColor(ILI9341_WHITE, PANEL);
  lcd.print(heapKb);
  lcd.print("K ");

  lcd.setTextColor(AMBER, PANEL);
  lcd.setCursor(90, 62);
  lcd.print("LUZ ");
  lcd.setTextColor(ILI9341_WHITE, PANEL);
  lcd.print(lightPct);
  lcd.print("%");

  lcd.setTextColor(aiBusy ? AMBER : GREEN, PANEL);
  lcd.setCursor(154, 62);
  lcd.print("IA ");
  lcd.print(aiStatus);

  lcd.drawRect(90, 76, 132, 5, 0x632C);
  lcd.fillRect(91, 77, map(q, 0, 100, 0, 130), 3, q > 60 ? GREEN : AMBER);
}

String extractJsonStringField(const String &json, const String &field) {
  String key = "\"" + field + "\":\"";
  int p = json.indexOf(key);
  if (p < 0) return "";
  p += key.length();
  String raw;
  bool esc = false;
  for (int i = p; i < json.length(); i++) {
    char c = json[i];
    if (esc) {
      raw += '\\';
      raw += c;
      esc = false;
    } else if (c == '\\') {
      esc = true;
    } else if (c == '"') {
      break;
    } else {
      raw += c;
    }
  }
  return jsonUnescape(raw);
}

bool extractJsonBoolField(const String &json, const String &field) {
  String key = "\"" + field + "\":";
  int p = json.indexOf(key);
  if (p < 0) return false;
  p += key.length();
  while (p < json.length() && json[p] == ' ') p++;
  return json.substring(p, p + 4) == "true";
}

uint8_t extractJsonOptions(const String &json, String *out) {
  int p = json.indexOf("\"opcoes\":[");
  if (p < 0) return 0;
  p += 10;
  uint8_t count = 0;
  while (p < json.length() && count < 3) {
    int q = json.indexOf('"', p);
    if (q < 0) break;
    int e = q + 1;
    bool esc = false;
    String raw;
    for (; e < json.length(); e++) {
      char c = json[e];
      if (esc) {
        raw += '\\';
        raw += c;
        esc = false;
      } else if (c == '\\') {
        esc = true;
      } else if (c == '"') {
        break;
      } else {
        raw += c;
      }
    }
    if (e >= json.length()) break;
    out[count++] = jsonUnescape(raw);
    p = e + 1;
    int close = json.indexOf(']', p);
    int nextQuote = json.indexOf('"', p);
    if (close >= 0 && (nextQuote < 0 || close < nextQuote)) break;
  }
  return count;
}

String callDeepSeekJson(const String &systemPrompt, const String &userJson) {
  if (WiFi.status() != WL_CONNECTED) return "";
  if (String(DEEPSEEK_API_KEY).length() < 10) return "";

  WiFiClientSecure client;
  client.setInsecure();
  client.setTimeout(20000);
  if (!client.connect("api.deepseek.com", 443)) return "";

  String body = "{\"model\":\"deepseek-v4-flash\",\"messages\":[";
  body += "{\"role\":\"system\",\"content\":\"" + jsonEscape(systemPrompt) + "\"},";
  body += "{\"role\":\"user\",\"content\":\"" + jsonEscape(userJson) + "\"}],";
  body += "\"thinking\":{\"type\":\"disabled\"},\"max_tokens\":170,\"stream\":false}";

  client.print("POST /chat/completions HTTP/1.1\r\n");
  client.print("Host: api.deepseek.com\r\n");
  client.print("Content-Type: application/json\r\n");
  client.print("Authorization: Bearer ");
  client.print(DEEPSEEK_API_KEY);
  client.print("\r\nContent-Length: ");
  client.print(body.length());
  client.print("\r\nConnection: close\r\n\r\n");
  client.print(body);

  String response;
  uint32_t deadline = millis() + 25000;
  while (millis() < deadline && (client.connected() || client.available())) {
    while (client.available()) {
      char c = client.read();
      if (response.length() < 12000) response += c;
    }
    delay(5);
  }
  if (response.indexOf(" 200 ") < 0) return "";
  return extractDeepSeekContent(response);
}

String tgSystemPrompt() {
  return "Voce e o nucleo conversacional profissional de um dispositivo fisico chamado Tamagotchi Reverso. Responda sempre sem acentos. O dispositivo pode ser usado como apoio psicoeducativo por profissionais de saude, mas nunca faz diagnostico, prescricao, prognostico clinico ou substitui medico, psicologo ou psiquiatra. Use raciocinio biopsicossocial breve: humor atual, perfil informado, tendencia recente, carga de trabalho, sono, sensibilidade sensorial, funcao executiva, energia e necessidade de apoio. Para depressao: baixa culpa, micro-acao, conexao humana, monitorar isolamento e desesperanca. Para autismo: linguagem concreta, previsibilidade, reduzir estimulo, respeitar sobrecarga. Para TDAH: reduzir friccao, proximo passo visivel, evitar moralizar procrastinacao. Para trabalho: detectar sinais de sobrecarga, conflito, prazo, fadiga decisoria e sugerir pausa, limite ou priorizacao. Regras: frase principal maximo 20 palavras; tom profissional, acolhedor e objetivo; sem cliche; considere escolha_anterior nas etapas 2 e 3; etapa final fecha sem pergunta aberta. Se tendencia ou escolhas sugerirem sofrimento intenso, desesperanca, risco ou isolamento perigoso, modo_seguranca_ativado=true e sugira falar com pessoa de confianca ou apoio profissional, sem alarmismo. Etapas 1 e 2 geram exatamente 2 opcoes com no maximo 6 palavras. Etapa 3 gera no maximo uma opcao Encerrar por hoje ou nenhuma. Nunca inclua texto fora do JSON. Saida JSON estrito: {\"frase\":\"...\",\"opcoes\":[\"...\"],\"is_final\":false,\"modo_seguranca_ativado\":false}";
}

String supportLabel(SupportKind kind) {
  switch (kind) {
    case SUPPORT_HELP_NOW: return "AJUDA AGORA";
    case SUPPORT_OVERLOAD: return "SOBRECARGA";
    case SUPPORT_MEETING: return "REUNIAO";
    case SUPPORT_THINKING: return "NAO CONSIGO PENSAR";
    case SUPPORT_IMPULSE: return "IMPULSO";
    case SUPPORT_ANXIETY: return "ANSIEDADE";
    case SUPPORT_LOW_MOOD: return "DESANIMO";
    case SUPPORT_LOW_ENERGY: return "SEM ENERGIA";
    case SUPPORT_ORGANIZE: return "ORGANIZAR";
    case SUPPORT_SILENT: return "SILENCIO";
    case SUPPORT_COMPANY: return "COMPANHIA";
    default: return "APOIO";
  }
}

String goalForSupport(SupportKind kind) {
  switch (kind) {
    case SUPPORT_MEETING: return "ATRAVESSAR A REUNIAO COM MENOS SOBRECARGA";
    case SUPPORT_IMPULSE: return "CRIAR DISTANCIA ANTES DE AGIR";
    case SUPPORT_ORGANIZE: return "ORGANIZAR OS PROXIMOS 15 MINUTOS";
    case SUPPORT_COMPANY: return "PERMANECER ACOMPANHADO";
    case SUPPORT_SILENT: return "REDUZIR ESTIMULOS EM SILENCIO";
    case SUPPORT_LOW_MOOD: return "CUIDAR DO MOMENTO SEM PRESSAO";
    case SUPPORT_LOW_ENERGY: return "REDUZIR A DEMANDA DE AGORA";
    case SUPPORT_ANXIETY: return "DIMINUIR O ALERTA UM PASSO";
    case SUPPORT_THINKING: return "RECUPERAR UM PROXIMO PASSO";
    default: return "AUMENTAR SEGURANCA E CLAREZA";
  }
}

String cycleStateLabel() {
  switch (cycleState) {
    case CYCLE_ACTIVE: return "ATIVO";
    case CYCLE_PAUSED: return "PAUSADO";
    case CYCLE_DISCREET: return "DISCRETO";
    case CYCLE_WAITING_HUMAN: return "AGUARDANDO APOIO";
    case CYCLE_STABLE: return "MAIS ESTAVEL";
    default: return "ENCERRADO";
  }
}

void setCompanionView(CompanionView next) {
  if (companionView != next) previousCompanionView = companionView;
  companionView = next;
  lcd.fillScreen(BG);
}

void startSupport(SupportKind kind) {
  supportKind = kind;
  cycleGoal = goalForSupport(kind);
  cycleLastAction = "";
  cycleResult = "";
  discomfortLevel = 0;
  interventionLevel = (kind == SUPPORT_HELP_NOW || kind == SUPPORT_IMPULSE) ? 3 : 1;
  actionStep = 0;
  contextStep = 0;
  compromisedCapacity = "nao informado";
  currentLocation = "nao informado";
  accompanimentState = "nao informado";
  canLeaveState = "nao informado";
  immediateEvent = "nao informado";
  needsActionNow = "nao informado";
  silentMode = kind == SUPPORT_SILENT;
  cycleState = silentMode ? CYCLE_DISCREET : CYCLE_ACTIVE;
  if (profileLearningConsent && (kind == SUPPORT_HELP_NOW || kind == SUPPORT_OVERLOAD)) {
    overloadPatternCount = min<uint8_t>(overloadPatternCount + 1, 99);
    saveProfile();
  }
  logInteraction("ciclo_iniciado", supportLabel(kind));
  saveCycle();
  setCompanionView(COMP_SAFETY);
}

void tgFallback(const String &humor, uint8_t step) {
  tgSafety = false;
  if (step == 1) {
    if (humor == "ansioso") {
      tgPhrase = profileWork ? "Seu alerta pode vir de carga alta; escolha o menor proximo passo." : "Seu corpo pode estar em alerta; vamos reduzir a carga por um passo.";
      tgOptions[0] = profileSensory || profileAutism ? "Baixar estimulo" : "Mapear gatilho";
      tgOptions[1] = profileTdah ? "Primeiro passo visivel" : "Uma acao pequena";
      tgOptionCount = 2;
    } else if (humor == "cansado") {
      tgPhrase = profileSleep ? "Cansaco repetido pede ajuste de sono, pausa e carga, nao cobranca." : "Cansaco tambem e informacao; talvez hoje precise de menos atrito.";
      tgOptions[0] = "Reduzir demanda"; tgOptions[1] = profileWork ? "Priorizar trabalho" : "Descanso possivel"; tgOptionCount = 2;
    } else if (humor == "pra baixo") {
      tgPhrase = profileDepression ? "Quando o peso repete, contato humano e rotina minima viram protecao." : "Quando tudo pesa, uma companhia real pode dividir parte do peso.";
      tgOptions[0] = "Falar com alguem"; tgOptions[1] = "Algo leve agora"; tgOptionCount = 2;
    } else if (humor == "radiante") {
      tgPhrase = "Esse momento bom merece registro, sem precisar virar obrigacao.";
      tgOptions[0] = "Guardar sinal"; tgOptions[1] = "Levar adiante"; tgOptionCount = 2;
    } else {
      tgPhrase = "Perceber o estado atual ja ajuda o proximo passo a ficar menor.";
      tgOptions[0] = "Nomear necessidade"; tgOptions[1] = "Uma dica simples"; tgOptionCount = 2;
    }
  } else if (step == 2) {
    tgPhrase = profileTdah ? "Transforme a intencao em acao visivel, curta e sem perfeccionismo." : "Sua escolha mostra uma necessidade real; vamos deixa-la pequena o bastante.";
    tgOptions[0] = profileWork ? "Ajustar prioridade" : "Proximo passo"; tgOptions[1] = "Encerrar por hoje"; tgOptionCount = 2;
  } else {
    tgPhrase = "Registro feito: humor, contexto e proximo passo podem orientar cuidado mais preciso.";
    tgOptionCount = 0;
  }
}

void tgCallJourney() {
  aiBusy = true;
  aiStatus = "PENSANDO";
  tgPhrase = "PENSANDO COM VOCE...";
  tgOptionCount = 0;
  lcd.fillScreen(BG);
  drawNeuralScreen();

  String used = "[";
  for (int i = 0; i < 4; i++) {
    if (tgUsedPhrases[i].length()) {
      if (used.length() > 1) used += ",";
      used += "\"" + jsonEscape(tgUsedPhrases[i]) + "\"";
    }
  }
  used += "]";
  String req = "{\"session_id\":\"esp32\",\"humor\":\"" + tgHumor + "\",\"etapa\":" + String(tgStep) + ",";
  req += "\"escolha_anterior\":" + (tgLastChoice.length() ? "\"" + jsonEscape(tgLastChoice) + "\"" : "null") + ",";
  req += "\"frases_ja_usadas\":" + used + ",";
  req += "\"perfil\":" + profileFlagsJson() + ",";
  req += "\"tendencia_recente\":" + trendJson() + ",";
  req += "\"contexto_dispositivo\":{\"wifi\":" + String(wifiQuality()) + ",\"heap_kb\":" + String(ESP.getFreeHeap() / 1024) + "}}";

  String json = callDeepSeekJson(tgSystemPrompt(), req);
  if (json.length() < 8) {
    tgFallback(tgHumor, tgStep);
  } else {
    String phrase = extractJsonStringField(json, "frase");
    if (phrase.length() == 0) tgFallback(tgHumor, tgStep);
    else {
      tgPhrase = phrase;
      tgOptionCount = extractJsonOptions(json, tgOptions);
      tgSafety = extractJsonBoolField(json, "modo_seguranca_ativado");
      if (extractJsonBoolField(json, "is_final")) tgOptionCount = 0;
    }
  }
  for (int i = 3; i > 0; i--) tgUsedPhrases[i] = tgUsedPhrases[i - 1];
  tgUsedPhrases[0] = tgPhrase;
  logInteraction("resposta_jornada", tgPhrase);
  aiStatus = String(DEEPSEEK_API_KEY).length() < 10 ? "LOCAL" : "DEEPSEEK";
  aiBusy = false;
  if (tgOptionCount > 2) tgOptionCount = 2;
  if (tgStep >= 3 || tgOptionCount == 0) tgView = 2;
  else tgView = 1;
  lcd.fillScreen(BG);
  drawNeuralScreen();
}

void tgStart(const String &humor) {
  tgHumor = humor;
  tgStep = 1;
  tgView = 1;
  tgLastChoice = "";
  tgSafety = false;
  for (int i = 0; i < 4; i++) tgUsedPhrases[i] = "";
  updateMoodTrend(humor);
  logInteraction("inicio_humor", humor);
  tgCallJourney();
}

void tgChoose(uint8_t index) {
  if (index >= tgOptionCount) return;
  tgLastChoice = tgOptions[index];
  logInteraction("escolha", tgLastChoice);
  tgStep++;
  if (tgStep > 3) tgStep = 3;
  tgCallJourney();
}

void tgReset() {
  tgView = 0;
  tgHumor = "";
  tgPhrase = "COMO VOCE ESTA AGORA?";
  tgOptionCount = 0;
  lcd.fillScreen(BG);
  drawNeuralScreen();
}

String actionForCurrentState() {
  if (silentMode) return "ESTOU AQUI. TOQUE QUANDO ESTIVER PRONTO.";
  if (actionStep == 0 && calmingPhrase.length()) return calmingPhrase;
  switch (supportKind) {
    case SUPPORT_MEETING:
      if (actionStep == 0) return "VOCE NAO PRECISA RESPONDER IMEDIATAMENTE.";
      if (actionStep == 1) return "ANOTE. DECIDA DEPOIS.";
      return "CONTINUE 5 MINUTOS OU PECA UMA PAUSA.";
    case SUPPORT_IMPULSE:
      if (actionStep == 0) return "CRIE 15 MINUTOS DE DISTANCIA ANTES DE AGIR.";
      if (actionStep == 1) return "ESCOLHA UMA ACAO QUE POSSA SER DESFEITA.";
      return "CONSULTE UMA PESSOA SEGURA ANTES DA DECISAO.";
    case SUPPORT_ORGANIZE:
      if (actionStep == 0) return "ESCOLHA APENAS O PROXIMO PASSO POSSIVEL.";
      if (actionStep == 1) return "SEPARE: AGORA, DEPOIS OU DELEGAR.";
      return "O QUE NAO PRECISA SER RESOLVIDO HOJE PODE ESPERAR.";
    case SUPPORT_LOW_MOOD:
      if (actionStep == 0) return "REDUZA O OBJETIVO DESTE MOMENTO.";
      if (actionStep == 1) return "VERIFIQUE AGUA, ALIMENTO, DESCANSO OU CONTATO HUMANO.";
      return "ESCOLHA UMA ACAO POSSIVEL, SEM SE COBRAR MAIS.";
    case SUPPORT_LOW_ENERGY:
      if (actionStep == 0) return "DIMINUA UMA DEMANDA QUE POSSA ESPERAR.";
      if (actionStep == 1) return "SENTE-SE OU APOIE O CORPO, SE FOR CONFORTAVEL.";
      return "CUIDE DE UMA NECESSIDADE BASICA AGORA.";
    case SUPPORT_COMPANY:
      if (actionStep == 0) return "POSSO FICAR AQUI SEM COBRAR RESPOSTA.";
      if (actionStep == 1) return "VOCE PODE IGNORAR ESTA TELA PELO TEMPO QUE PRECISAR.";
      return "QUANDO QUISER, CONTINUE OU CHAME ALGUEM.";
    case SUPPORT_ANXIETY:
      if (actionStep == 0) return "APOIE OS PES OU O CORPO, SE FOR CONFORTAVEL.";
      if (actionStep == 1) return "RESPIRE NATURALMENTE. NAO PRECISA FORCAR O RITMO.";
      return "REDUZA SOM, LUZ OU MOVIMENTO AO SEU REDOR.";
    case SUPPORT_THINKING:
      if (actionStep == 0) return "NAO TENTE RESOLVER TUDO AGORA.";
      if (actionStep == 1) return "ADIE DECISOES IMPORTANTES POR ENQUANTO.";
      return "ESCOLHA UMA ACAO PEQUENA E REVERSIVEL.";
    default:
      if (actionStep == 0) return "SENTE-SE OU APOIE O CORPO, SE FOR CONFORTAVEL.";
      if (actionStep == 1) return "REDUZA LUZ, SOM E MOVIMENTO AO REDOR.";
      return "NAO TOME DECISOES IRREVERSIVEIS AGORA.";
  }
}

void selectIntensity(uint8_t value) {
  discomfortLevel = value;
  if (value >= 4 || supportKind == SUPPORT_HELP_NOW || supportKind == SUPPORT_IMPULSE) interventionLevel = 3;
  else if (value >= 2) interventionLevel = 2;
  else interventionLevel = 1;
  saveCycle();
  setCompanionView(interventionLevel >= 3 ? COMP_ACTION : COMP_CAPACITY);
}

void recordActionAndCheckIn() {
  cycleLastAction = actionForCurrentState();
  logInteraction("acao_oferecida", cycleLastAction);
  saveCycle();
  setCompanionView(COMP_CHECKIN);
}

void requestHumanSupport() {
  cycleState = CYCLE_WAITING_HUMAN;
  saveCycle();
  logInteraction("apoio_humano", trustedName.length() ? trustedName : "nao configurado");
  setCompanionView(COMP_CONTACT);
}

void drawMoodButton(int x, int y, int w, int h, const String &label, uint16_t color) {
  lcd.fillRoundRect(x, y, w, h, 5, color);
  lcd.setTextColor(ILI9341_BLACK, color);
  lcd.setTextSize(1);
  lcd.setCursor(x + 8, y + h / 2 - 2);
  lcd.print(label);
}

void drawTamagotchiHome() {
  drawTopNav();
  lcd.fillRoundRect(12, 34, 216, 44, 6, PANEL);
  lcd.fillCircle(42, 55, 14, CYAN);
  lcd.fillCircle(37, 52, 2, ILI9341_BLACK);
  lcd.fillCircle(47, 52, 2, ILI9341_BLACK);
  lcd.drawFastHLine(37, 60, 11, ILI9341_BLACK);
  lcd.setTextColor(ILI9341_WHITE, PANEL);
  lcd.setTextSize(1);
  lcd.setCursor(66, 46);
  lcd.print("TAMAGOTCHI REVERSO");
  lcd.setCursor(66, 62);
  lcd.print("ELE ALIMENTA VOCE");

  drawTextBox(12, 84, 216, 28, "HUMOR", tgPhrase, CYAN);
  drawMoodButton(12, 122, 66, 28, "RADIANTE", AMBER);
  drawMoodButton(86, 122, 66, 28, "BEM", GREEN);
  drawMoodButton(160, 122, 68, 28, "NEUTRO", 0xBDF7);
  drawMoodButton(12, 158, 66, 28, "CANSADO", CYAN);
  drawMoodButton(86, 158, 66, 28, "ANSIOSO", 0xFD20);
  drawMoodButton(160, 158, 68, 28, "PRA BAIXO", PINK);
  lcd.setTextColor(MUTED, BG);
  lcd.setCursor(18, 206);
  lcd.print("TOQUE NO HUMOR PARA COMECAR.");
}

void drawTamagotchiJourney() {
  drawTopNav();
  lcd.fillRoundRect(10, 34, 220, 36, 6, PANEL);
  lcd.setTextColor(CYAN, PANEL);
  lcd.setTextSize(1);
  lcd.setCursor(18, 46);
  lcd.print("HUMOR ");
  lcd.setTextColor(ILI9341_WHITE, PANEL);
  lcd.print(tgHumor);
  lcd.setTextColor(AMBER, PANEL);
  lcd.setCursor(150, 46);
  lcd.print("ETAPA ");
  lcd.print(tgStep);

  drawTextBox(10, 78, 220, 62, "REFLEXAO", tgPhrase, tgSafety ? AMBER : PINK);
  if (tgSafety) {
    drawMoodButton(14, 150, 212, 28, "FALAR COM ALGUEM AGORA", AMBER);
    drawMoodButton(14, 188, 212, 28, "ENCERRAR POR HOJE", PINK);
    return;
  }
  for (int i = 0; i < tgOptionCount; i++) {
    int by = 152 + i * 42;
    drawMoodButton(14, by, 212, 32, tgOptions[i], i == 0 ? CYAN : GREEN);
  }
}

void drawTamagotchiFinal() {
  drawTopNav();
  drawTextBox(10, 36, 220, 62, "FECHAMENTO", tgPhrase, GREEN);
  lcd.setTextColor(MUTED, BG);
  lcd.setTextSize(1);
  lcd.setCursor(18, 108);
  lcd.print("SEU HUMOR MUDOU?");
  for (int i = 0; i < 5; i++) drawMoodButton(14 + i * 43, 124, 36, 26, String(i + 1), CYAN);
  lcd.setCursor(18, 164);
  lcd.print("ISSO TE AJUDOU?");
  drawMoodButton(14, 182, 56, 26, "SIM", GREEN);
  drawMoodButton(78, 182, 82, 26, "MAIS OU MENOS", AMBER);
  drawMoodButton(168, 182, 58, 26, "NAO", PINK);
}

void drawLegacyTamagotchi() {
  if (tgView == 0) drawTamagotchiHome();
  else if (tgView == 1) drawTamagotchiJourney();
  else drawTamagotchiFinal();
}

void handleLegacyTamagotchiTouch(uint16_t x, uint16_t y) {
  if (y < 28) {
    screen = min((int)(x / (lcd.width() / 4)), 3);
    lcd.fillScreen(BG);
    previousScreen = 255;
    if (screen == 1) scanWifi();
    return;
  }
  if (tgView == 0) {
    if (y >= 122 && y < 150) {
      if (x < 82) tgStart("radiante");
      else if (x < 156) tgStart("bem");
      else tgStart("neutro");
    } else if (y >= 158 && y < 186) {
      if (x < 82) tgStart("cansado");
      else if (x < 156) tgStart("ansioso");
      else tgStart("pra baixo");
    }
    return;
  }
  if (tgView == 1) {
    if (tgSafety) {
      if (y >= 150 && y < 216) {
        tgView = 2;
        drawNeuralScreen();
      }
      return;
    }
    for (int i = 0; i < tgOptionCount; i++) {
      int by = 152 + i * 42;
      if (x >= 14 && x <= 226 && y >= by && y < by + 32) {
        tgChoose(i);
        return;
      }
    }
    return;
  }
  if (tgView == 2) {
    if (y >= 124 && y < 150 && x >= 14 && x < 229) {
      int note = constrain(((int)x - 14) / 43 + 1, 1, 5);
      Serial.print("LOG: humor=");
      Serial.print(tgHumor);
      Serial.print(" nota=");
      Serial.println(note);
      logInteraction("nota_humor", String(note));
    } else if (y >= 182 && y < 208) {
      Serial.print("LOG: efeito=");
      if (x < 74) {
        Serial.println("sim");
        logInteraction("efeito", "sim");
      } else if (x < 164) {
        Serial.println("mais_ou_menos");
        logInteraction("efeito", "mais_ou_menos");
      } else {
        Serial.println("nao");
        logInteraction("efeito", "nao");
      }
      tgReset();
    }
  }
}

void drawChoiceButton(int x, int y, int w, int h, const String &label, uint16_t color) {
  lcd.fillRect(x, y, w, h, color);
  lcd.setTextColor(ILI9341_BLACK, color);
  lcd.setTextSize(1);
  int tx = x + max(4, (w - (int)asciiText(label).length() * 4) / 2);
  lcd.setCursor(tx, y + h / 2 - 2);
  lcd.print(asciiText(label));
}

void drawCycleControls() {
  const char *labels[] = {"VOLTAR", "PAUSA", "SILENC", "GUIA", "FIM"};
  for (int i = 0; i < 5; i++) {
    uint16_t bg = i == 2 && silentMode ? CYAN : (i == 4 ? 0xD6BA : 0x2104);
    drawChoiceButton(i * 64, 0, 63, 27, labels[i], bg);
  }
}

void drawCompanionHome() {
  drawTopNav();
  lcd.setTextColor(CYAN, BG);
  lcd.setTextSize(2);
  lcd.setCursor(8, 34);
  lcd.print("ESTOU AQUI.");
  lcd.setTextColor(ILI9341_WHITE, BG);
  lcd.setTextSize(1);
  lcd.setCursor(8, 55);
  lcd.print("VOCE NAO PRECISA EXPLICAR TUDO AGORA.");

  const char *page0[] = {"AJUDA AGORA", "SOBRECARGA", "EM REUNIAO", "NAO CONSIGO PENSAR", "IMPULSO", "MAIS OPCOES"};
  const char *page1[] = {"ANSIOSO", "TRISTE OU DESANIMO", "SEM ENERGIA", "ORGANIZAR O DIA", "FICAR EM SILENCIO", "SO COMPANHIA"};
  const char **labels = homePage == 0 ? page0 : page1;
  uint16_t colors[] = {PINK, CYAN, AMBER, GREEN, 0xFD20, 0xBDF7};
  for (int i = 0; i < 6; i++) {
    int x = 8 + (i % 2) * 154;
    int y = 72 + (i / 2) * 43;
    drawChoiceButton(x, y, 146, 35, labels[i], colors[i]);
  }
  if (homePage == 1) drawChoiceButton(8, 204, 304, 28, "VOLTAR AS OPCOES", 0x7BEF);
  else if (predictionConsent && overloadPatternCount >= 3) {
    drawWrapped(8, 204, 304, 26, "HA SINAIS DE SOBRECARGA REPETIDA. CONSIDERE UMA PAUSA.", AMBER, BG, 1);
  }
}

void drawResumeCycle() {
  drawCycleControls();
  drawTextBox(8, 36, 304, 56, "RETOMAR", "NA ULTIMA INTERACAO, VOCE ESTAVA TENTANDO: " + cycleGoal, CYAN);
  drawTextBox(8, 100, 304, 42, "ESTADO", cycleStateLabel(), AMBER);
  drawChoiceButton(8, 154, 304, 32, "ISSO AINDA ESTA ACONTECENDO", GREEN);
  drawChoiceButton(8, 194, 304, 32, "ENCERRAR ESTE CICLO", 0xD6BA);
}

void drawSafetyQuestion() {
  drawCycleControls();
  drawTextBox(8, 38, 304, 66, "SEGURANCA", "VOCE ESTA EM UM LUGAR FISICAMENTE SEGURO?", PINK);
  drawChoiceButton(8, 118, 96, 42, "SIM", GREEN);
  drawChoiceButton(112, 118, 96, 42, "NAO", PINK);
  drawChoiceButton(216, 118, 96, 42, "NAO SEI", AMBER);
  drawWrapped(12, 176, 296, 44, "UMA RESPOSTA BASTA. NAO PRECISA EXPLICAR.", MUTED, BG, 1);
}

void drawIntensityQuestion() {
  drawCycleControls();
  drawTextBox(8, 38, 304, 54, "AGORA", "QUAL O NIVEL DE DESCONFORTO?", CYAN);
  for (int i = 0; i < 5; i++) drawChoiceButton(8 + i * 61, 108, 54, 46, String(i + 1), i < 2 ? GREEN : (i < 4 ? AMBER : PINK));
  drawChoiceButton(8, 172, 299, 38, "NAO SEI", 0xBDF7);
}

void drawCapacityQuestion() {
  drawCycleControls();
  drawTextBox(8, 36, 304, 52, "UMA PERGUNTA", "O QUE ESTA MAIS DIFICIL AGORA?", CYAN);
  const char *labels[] = {"COMUNICAR", "CONCENTRAR", "DECIDIR", "PERCEBER O CORPO", "MEMORIA OU ORIENTAR", "REGULAR EMOCOES", "TOLERAR ESTIMULOS", "NAO SEI"};
  uint16_t colors[] = {CYAN, GREEN, AMBER, 0xBDF7, CYAN, GREEN, PINK, 0x7BEF};
  for (int i = 0; i < 8; i++) {
    int x = 8 + (i % 2) * 154;
    int y = 96 + (i / 2) * 34;
    drawChoiceButton(x, y, 146, 28, labels[i], colors[i]);
  }
}

void drawContextQuestion() {
  drawCycleControls();
  if (contextStep == 0) {
    drawTextBox(8, 36, 304, 52, "CONTEXTO", "ONDE VOCE ESTA?", CYAN);
    const char *labels[] = {"CASA", "TRABALHO", "RUA", "OUTRO"};
    for (int i = 0; i < 4; i++) drawChoiceButton(8 + (i % 2) * 154, 106 + (i / 2) * 46, 146, 36, labels[i], i < 2 ? GREEN : AMBER);
  } else if (contextStep == 1) {
    drawTextBox(8, 36, 304, 52, "CONTEXTO", "VOCE ESTA SOZINHO?", CYAN);
    drawChoiceButton(8, 108, 96, 42, "SIM", AMBER);
    drawChoiceButton(112, 108, 96, 42, "NAO", GREEN);
    drawChoiceButton(216, 108, 96, 42, "NAO SEI", 0xBDF7);
  } else if (contextStep == 2) {
    drawTextBox(8, 36, 304, 52, "CONTEXTO", "VOCE PODE SAIR DE ONDE ESTA?", CYAN);
    drawChoiceButton(8, 108, 96, 42, "SIM", GREEN);
    drawChoiceButton(112, 108, 96, 42, "NAO", AMBER);
    drawChoiceButton(216, 108, 96, 42, "NAO SEI", 0xBDF7);
  } else if (contextStep == 3) {
    drawTextBox(8, 36, 304, 52, "ANTES", "O QUE ACONTECEU LOGO ANTES?", CYAN);
    const char *labels[] = {"MUITO ESTIMULO", "CONFLITO", "COBRANCA OU PRAZO", "MUDANCA", "DOR OU FOME", "NAO SEI"};
    for (int i = 0; i < 6; i++) drawChoiceButton(8 + (i % 2) * 154, 98 + (i / 2) * 40, 146, 32, labels[i], i == 5 ? 0x7BEF : AMBER);
  } else {
    drawTextBox(8, 36, 304, 52, "AGORA", "VOCE PRECISA AGIR AGORA?", CYAN);
    drawChoiceButton(8, 106, 304, 34, "SIM, PRECISO DE UMA ACAO", AMBER);
    drawChoiceButton(8, 150, 304, 34, "NAO, POSSO SER ACOMPANHADO", GREEN);
    drawChoiceButton(8, 194, 304, 32, "NAO SEI", 0xBDF7);
  }
}

void drawRegulationAction() {
  drawCycleControls();
  lcd.setTextColor(MUTED, BG);
  lcd.setTextSize(1);
  lcd.setCursor(8, 33);
  lcd.print(supportLabel(supportKind));
  lcd.setCursor(238, 33);
  lcd.print("NIVEL ");
  lcd.print(interventionLevel);
  String title = guidanceLevel == 0 ? "AGORA" : "UMA ACAO AGORA";
  drawTextBox(8, 48, 304, 78, title, actionForCurrentState(), silentMode ? CYAN : GREEN);
  drawChoiceButton(8, 140, 146, 34, silentMode ? "ESTOU AQUI" : "FIZ ISSO", GREEN);
  drawChoiceButton(162, 140, 150, 34, "OUTRA ACAO", CYAN);
  drawChoiceButton(8, 186, 304, 34, "CHAMAR APOIO HUMANO", AMBER);
}

void drawCheckIn() {
  drawCycleControls();
  drawTextBox(8, 38, 304, 60, "SEM PRESSA", "COMO ESTA A INTENSIDADE AGORA?", CYAN);
  drawChoiceButton(8, 114, 96, 44, "MELHOR", GREEN);
  drawChoiceButton(112, 114, 96, 44, "IGUAL", AMBER);
  drawChoiceButton(216, 114, 96, 44, "PIOR", PINK);
  drawChoiceButton(8, 180, 304, 36, "PRECISO DE UMA PESSOA", 0xBDF7);
}

void drawContactScreen() {
  drawCycleControls();
  String who = trustedName.length() ? trustedName : "UMA PESSOA SEGURA";
  String detail = "PROCURE OU LIGUE PARA " + who + ".";
  if (trustedPhone.length()) detail += " NUMERO: " + trustedPhone;
  drawTextBox(8, 38, 304, 76, "APOIO HUMANO", detail, AMBER);
  drawChoiceButton(8, 132, 304, 36, "JA ESTOU COM ALGUEM", GREEN);
  drawChoiceButton(8, 180, 304, 36, "CONTINUAR ACOMPANHADO", CYAN);
}

void drawEmergencyScreen() {
  drawCycleControls();
  drawTextBox(8, 36, 304, 92, "SEGURANCA PRIMEIRO", "PROCURE UMA PESSOA SEGURA OU ATENDIMENTO PRESENCIAL AGORA. ESTE DISPOSITIVO NAO CONDUZ UMA EMERGENCIA SOZINHO.", PINK);
  drawChoiceButton(8, 142, 304, 34, "CHAMAR UMA PESSOA SEGURA", AMBER);
  drawChoiceButton(8, 186, 304, 34, "FICAR COMIGO ENQUANTO ISSO", CYAN);
}

void drawPausedCycle() {
  drawCycleControls();
  drawTextBox(8, 52, 304, 70, "PAUSADO", "NAO VOU COBRAR RESPOSTA. O CICLO CONTINUA DISPONIVEL.", CYAN);
  drawChoiceButton(8, 142, 304, 38, "RETOMAR", GREEN);
  drawChoiceButton(8, 190, 304, 32, "ENCERRAR", 0xD6BA);
}

void drawCloseQuestion() {
  drawCycleControls();
  drawTextBox(8, 36, 304, 62, "ANTES DE ENCERRAR", "VOCE CONSEGUE CONTINUAR EM SEGURANCA?", GREEN);
  drawChoiceButton(8, 112, 304, 32, "SIM, MAIS ESTAVEL", GREEN);
  drawChoiceButton(8, 154, 304, 32, "PRECISO DE COMPANHIA", CYAN);
  drawChoiceButton(8, 196, 304, 32, "PRECISO FALAR COM ALGUEM", AMBER);
}

void drawCycleSummary() {
  drawCycleControls();
  String happened = supportLabel(supportKind) + " / " + immediateEvent + " / NIVEL " + String(discomfortLevel ? discomfortLevel : interventionLevel);
  drawTextBox(8, 34, 304, 44, "O QUE ACONTECEU", happened, PINK);
  drawTextBox(8, 84, 304, 52, "O QUE AJUDOU", cycleLastAction.length() ? cycleLastAction : "ACOMPANHAMENTO E REDUCAO DE DEMANDAS", GREEN);
  drawTextBox(8, 142, 304, 42, "PROXIMO CUIDADO", cycleResult, AMBER);
  drawChoiceButton(8, 194, 304, 32, "FINALIZAR POR AGORA", CYAN);
}

void drawTamagotchi() {
  switch (companionView) {
    case COMP_HOME: drawCompanionHome(); break;
    case COMP_RESUME: drawResumeCycle(); break;
    case COMP_SAFETY: drawSafetyQuestion(); break;
    case COMP_INTENSITY: drawIntensityQuestion(); break;
    case COMP_CAPACITY: drawCapacityQuestion(); break;
    case COMP_CONTEXT: drawContextQuestion(); break;
    case COMP_ACTION: drawRegulationAction(); break;
    case COMP_CHECKIN: drawCheckIn(); break;
    case COMP_CONTACT: drawContactScreen(); break;
    case COMP_EMERGENCY: drawEmergencyScreen(); break;
    case COMP_PAUSED: drawPausedCycle(); break;
    case COMP_CLOSE: drawCloseQuestion(); break;
    case COMP_SUMMARY: drawCycleSummary(); break;
  }
}

void redrawCompanion() {
  lcd.fillScreen(BG);
  drawTamagotchi();
}

void handleTamagotchiTouch(uint16_t x, uint16_t y) {
  if (companionView == COMP_HOME) {
    if (y < 28) {
      screen = min((int)(x / (lcd.width() / 4)), 3);
      lcd.fillScreen(BG);
      previousScreen = 255;
      if (screen == 1) scanWifi();
      return;
    }
    if (homePage == 1 && y >= 204) {
      homePage = 0;
      redrawCompanion();
      return;
    }
    if (y < 72 || y >= 193) return;
    int row = (y - 72) / 43;
    int col = x < 160 ? 0 : 1;
    int index = row * 2 + col;
    if (index < 0 || index > 5) return;
    if (homePage == 0) {
      SupportKind kinds[] = {SUPPORT_HELP_NOW, SUPPORT_OVERLOAD, SUPPORT_MEETING, SUPPORT_THINKING, SUPPORT_IMPULSE, SUPPORT_NONE};
      if (index == 5) {
        homePage = 1;
        redrawCompanion();
      } else startSupport(kinds[index]);
    } else {
      SupportKind kinds[] = {SUPPORT_ANXIETY, SUPPORT_LOW_MOOD, SUPPORT_LOW_ENERGY, SUPPORT_ORGANIZE, SUPPORT_SILENT, SUPPORT_COMPANY};
      startSupport(kinds[index]);
    }
    return;
  }

  if (y < 28) {
    int control = min((int)(x / 64), 4);
    if (control == 0) {
      CompanionView target = previousCompanionView;
      previousCompanionView = companionView;
      companionView = target;
    } else if (control == 1) {
      cycleState = CYCLE_PAUSED;
      saveCycle();
      setCompanionView(COMP_PAUSED);
    } else if (control == 2) {
      silentMode = !silentMode;
      cycleState = silentMode ? CYCLE_DISCREET : CYCLE_ACTIVE;
      saveCycle();
    } else if (control == 3) {
      guidanceLevel = (guidanceLevel + 1) % 3;
      saveProfile();
    } else {
      setCompanionView(COMP_CLOSE);
    }
    redrawCompanion();
    return;
  }

  if (companionView == COMP_RESUME) {
    if (y >= 154 && y < 188) {
      cycleState = silentMode ? CYCLE_DISCREET : CYCLE_ACTIVE;
      saveCycle();
      setCompanionView(COMP_ACTION);
    } else if (y >= 194 && y < 228) setCompanionView(COMP_CLOSE);
  } else if (companionView == COMP_SAFETY && y >= 118 && y < 162) {
    if (x < 104) setCompanionView(COMP_INTENSITY);
    else {
      interventionLevel = 4;
      cycleState = CYCLE_WAITING_HUMAN;
      cycleResult = "APOIO HUMANO OU ATENDIMENTO PRESENCIAL";
      saveCycle();
      setCompanionView(COMP_EMERGENCY);
    }
  } else if (companionView == COMP_INTENSITY) {
    if (y >= 108 && y < 156 && x < 313) selectIntensity(constrain((int)x / 61 + 1, 1, 5));
    else if (y >= 172 && y < 212) selectIntensity(4);
  } else if (companionView == COMP_CAPACITY && y >= 96 && y < 232) {
    int row = (y - 96) / 34;
    int col = x < 160 ? 0 : 1;
    int index = constrain(row * 2 + col, 0, 7);
    const char *values[] = {"comunicacao", "concentracao", "decisao", "percepcao corporal", "memoria ou orientacao", "regulacao emocional", "tolerancia sensorial", "nao sei"};
    compromisedCapacity = values[index];
    contextStep = 0;
    saveCycle();
    setCompanionView(COMP_CONTEXT);
  } else if (companionView == COMP_CONTEXT) {
    if (contextStep == 0 && y >= 106 && y < 188) {
      int index = constrain(((y - 106) / 46) * 2 + (x < 160 ? 0 : 1), 0, 3);
      const char *values[] = {"casa", "trabalho", "rua", "outro"};
      currentLocation = values[index];
      contextStep++;
    } else if ((contextStep == 1 || contextStep == 2) && y >= 108 && y < 152) {
      String value = x < 104 ? "sim" : (x < 212 ? "nao" : "nao sei");
      if (contextStep == 1) accompanimentState = value;
      else canLeaveState = value;
      contextStep++;
    } else if (contextStep == 3 && y >= 98 && y < 218) {
      int index = constrain(((y - 98) / 40) * 2 + (x < 160 ? 0 : 1), 0, 5);
      const char *values[] = {"muito estimulo", "conflito", "cobranca ou prazo", "mudanca", "dor ou fome", "nao sei"};
      immediateEvent = values[index];
      contextStep++;
    } else if (contextStep == 4) {
      if (y >= 106 && y < 142) needsActionNow = "sim";
      else if (y >= 150 && y < 186) needsActionNow = "nao";
      else if (y >= 194 && y < 228) needsActionNow = "nao sei";
      else return;
      saveCycle();
      setCompanionView(COMP_ACTION);
    } else return;
    saveCycle();
  } else if (companionView == COMP_ACTION) {
    if (y >= 140 && y < 176) {
      if (x < 158) recordActionAndCheckIn();
      else {
        actionStep = min<uint8_t>(actionStep + 1, 2);
        saveCycle();
      }
    } else if (y >= 186 && y < 222) requestHumanSupport();
  } else if (companionView == COMP_CHECKIN) {
    if (y >= 114 && y < 160) {
      if (x < 104) {
        cycleState = CYCLE_STABLE;
        cycleResult = "MANTER PAUSA E ADIAR DECISOES IMPORTANTES";
        saveCycle();
        setCompanionView(COMP_CLOSE);
      } else if (x < 212) {
        actionStep = min<uint8_t>(actionStep + 1, 2);
        saveCycle();
        setCompanionView(COMP_ACTION);
      } else {
        interventionLevel = 3;
        saveCycle();
        setCompanionView(COMP_SAFETY);
      }
    } else if (y >= 180 && y < 218) requestHumanSupport();
  } else if (companionView == COMP_CONTACT) {
    if (y >= 132 && y < 170) {
      cycleResult = "CONTINUAR COM APOIO HUMANO";
      setCompanionView(COMP_CLOSE);
    } else if (y >= 180 && y < 218) setCompanionView(COMP_ACTION);
  } else if (companionView == COMP_EMERGENCY) {
    if (y >= 142 && y < 178) requestHumanSupport();
    else if (y >= 186 && y < 222) {
      silentMode = true;
      cycleState = CYCLE_WAITING_HUMAN;
      saveCycle();
      setCompanionView(COMP_CONTACT);
    }
  } else if (companionView == COMP_PAUSED) {
    if (y >= 142 && y < 182) {
      cycleState = silentMode ? CYCLE_DISCREET : CYCLE_ACTIVE;
      saveCycle();
      setCompanionView(COMP_ACTION);
    } else if (y >= 190 && y < 224) setCompanionView(COMP_CLOSE);
  } else if (companionView == COMP_CLOSE) {
    if (y >= 112 && y < 146) {
      cycleState = CYCLE_STABLE;
      if (!cycleResult.length()) cycleResult = "NOVO CONTATO CONFORME SUA NECESSIDADE";
      saveCycle();
      setCompanionView(COMP_SUMMARY);
    } else if (y >= 154 && y < 188) {
      supportKind = SUPPORT_COMPANY;
      cycleState = CYCLE_ACTIVE;
      saveCycle();
      setCompanionView(COMP_ACTION);
    } else if (y >= 196 && y < 230) requestHumanSupport();
  } else if (companionView == COMP_SUMMARY && y >= 194 && y < 228) {
    logInteraction("ciclo_encerrado", cycleResult);
    clearCycle();
    companionView = COMP_HOME;
    previousCompanionView = COMP_HOME;
    homePage = 0;
  }
  redrawCompanion();
}

void drawAiAnswer() {
  card(8, 86, 224, 66, "RESPOSTA / DOCUMENTO", PINK);
  lcd.setTextColor(aiBusy ? AMBER : GREEN, PANEL);
  lcd.setTextSize(1);
  lcd.setCursor(154, 94);
  lcd.print(aiStatus);
  drawWrapped(18, 112, 204, 32, aiAnswer, ILI9341_WHITE, PANEL, 1);
}

void drawQuestionInputHint() {
  card(8, 158, 224, 48, "PERGUNTAR", GREEN);
  lcd.setTextColor(MUTED, PANEL);
  lcd.setTextSize(1);
  lcd.setCursor(16, 166);
  lcd.print(WiFi.status() == WL_CONNECTED ? ipText() : "SEM WIFI");
  drawAiButton(14, 180, 66, 22, "RESUMO", CYAN);
  drawAiButton(86, 180, 66, 22, "STATUS", AMBER);
  drawAiButton(158, 180, 68, 22, "SERVIDOR", PINK);
}

void drawNeuralScreen() {
  drawTamagotchi();
}

void startInputServer() {
  if (inputServerStarted) return;
  inputServer.begin();
  inputServerStarted = true;
  Serial.print("HTTP: input server http://");
  Serial.println(WiFi.localIP());
}

String formField(const String &body, const String &name) {
  String wrapped = "&" + body;
  String key = "&" + name + "=";
  int start = wrapped.indexOf(key);
  if (start < 0) return "";
  start += key.length();
  int end = wrapped.indexOf('&', start);
  if (end < 0) end = wrapped.length();
  String value = urlDecode(wrapped.substring(start, end));
  if (value.length() > 300) value = value.substring(0, 300);
  return value;
}

bool formChecked(const String &body, const String &name) {
  String wrapped = "&" + body;
  return wrapped.indexOf("&" + name + "=on") >= 0;
}

String profileFieldHtml(const String &name, const String &label, const String &value, bool multiline = true) {
  String out = "<label>" + label;
  if (multiline) out += "<textarea name='" + name + "'>" + htmlEscape(value) + "</textarea>";
  else out += "<input name='" + name + "' value='" + htmlEscape(value) + "'>";
  out += "</label>";
  return out;
}

void erasePersonalData() {
  prefs.begin("profile", false);
  prefs.clear();
  prefs.end();
  clearCycle();
  profileDepression = false;
  profileAutism = false;
  profileTdah = false;
  profileSensory = false;
  profileSleep = false;
  profileWork = false;
  preferredName = "";
  profileAge = "";
  trustedName = "";
  trustedPhone = "";
  profileNeuro = "";
  relevantConditions = "";
  sensoryNotes = "";
  earlySignals = "";
  worseningSignals = "";
  knownTriggers = "";
  stressSituations = "";
  helpfulStrategies = "";
  harmfulStrategies = "";
  communicationPreference = "toques e texto curto";
  calmingPhrase = "";
  phrasesToAvoid = "";
  treatmentNotes = "";
  routineNotes = "";
  personalGoals = "";
  personalLimits = "";
  autonomyLevel = 2;
  guidanceLevel = 1;
  overloadPatternCount = 0;
  profileLearningConsent = false;
  predictionConsent = false;
  cloudProfileConsent = false;
  eraseConfirm = false;
  companionView = COMP_HOME;
}

void sendInputPage(WiFiClient &client, const String &message) {
  String page;
  page.reserve(14000);
  page += "<!doctype html><html lang='pt-BR'><head><meta name='viewport' content='width=device-width,initial-scale=1'>";
  page += "<title>Perfil do acompanhante</title><style>";
  page += "*{box-sizing:border-box}body{font-family:system-ui;background:#f4f6f7;color:#172026;margin:0;line-height:1.45}";
  page += "header,main{max-width:760px;margin:auto;padding:20px}header{background:#12343b;color:white;max-width:none}header div{max-width:760px;margin:auto}";
  page += "h1{font-size:26px;margin:0}h2{font-size:18px;margin:0 0 14px}.section{padding:22px 20px;border-bottom:1px solid #ccd5d8}";
  page += "label{display:block;font-weight:700;margin:12px 0}input,textarea,select{display:block;width:100%;margin-top:6px;padding:11px;border:1px solid #87989e;border-radius:4px;background:white;font:inherit}";
  page += "textarea{min-height:76px;resize:vertical}.check{display:flex;gap:10px;align-items:flex-start;font-weight:500}.check input{width:20px;margin:2px 0}";
  page += "button{width:100%;padding:14px;border:0;border-radius:4px;background:#087f8c;color:white;font-weight:800;font-size:16px}.danger{background:#a3323a}.notice{padding:12px;border-left:4px solid #d39418;background:#fff8e8;margin:12px 0}";
  page += "</style></head><body><header><div><h1>ACOMPANHANTE</h1><p>Perfil adaptativo e privacidade</p></div></header><main>";
  if (message.length()) page += "<p class='notice'>" + htmlEscape(message) + "</p>";
  page += "<form action='/profile' method='post'>";
  page += "<section class='section'><h2>Como acompanhar voce</h2>";
  page += profileFieldHtml("name", "Nome ou forma de tratamento", preferredName, false);
  page += profileFieldHtml("age", "Idade", profileAge, false);
  page += profileFieldHtml("neuro", "Neurodivergencias conhecidas ou suspeitas", profileNeuro);
  page += profileFieldHtml("conditions", "Condicoes emocionais ou cognitivas relevantes", relevantConditions);
  page += profileFieldHtml("communication", "Forma de comunicacao preferida", communicationPreference);
  page += "<label>Autonomia durante uma crise<select name='autonomy'>";
  page += "<option value='1'" + String(autonomyLevel == 1 ? " selected" : "") + ">Mais orientacao</option>";
  page += "<option value='2'" + String(autonomyLevel == 2 ? " selected" : "") + ">Equilibrada</option>";
  page += "<option value='3'" + String(autonomyLevel == 3 ? " selected" : "") + ">Mais escolhas e autonomia</option></select></label></section>";
  page += "<section class='section'><h2>Sinais e sensibilidades</h2>";
  page += profileFieldHtml("sensory", "Sensibilidades sensoriais", sensoryNotes);
  page += profileFieldHtml("early", "Sinais iniciais de sobrecarga", earlySignals);
  page += profileFieldHtml("worse", "Sinais de agravamento", worseningSignals);
  page += profileFieldHtml("triggers", "Gatilhos conhecidos", knownTriggers);
  page += profileFieldHtml("stress", "Situacoes que normalmente geram estresse", stressSituations) + "</section>";
  page += "<section class='section'><h2>O que ajuda</h2>";
  page += profileFieldHtml("helps", "Estrategias que costumam ajudar", helpfulStrategies);
  page += profileFieldHtml("harms", "Estrategias que pioram", harmfulStrategies);
  page += profileFieldHtml("calm", "Frases que acalmam", calmingPhrase);
  page += profileFieldHtml("avoid", "Frases que incomodam ou invalidam", phrasesToAvoid) + "</section>";
  page += "<section class='section'><h2>Continuidade do cuidado</h2>";
  page += profileFieldHtml("trust_name", "Pessoa de confianca", trustedName, false);
  page += profileFieldHtml("trust_phone", "Telefone da pessoa de confianca", trustedPhone, false);
  page += profileFieldHtml("treatment", "Medicamentos ou tratamentos informados", treatmentNotes);
  page += profileFieldHtml("routine", "Rotina de sono, alimentacao, estudo e trabalho", routineNotes);
  page += profileFieldHtml("goals", "Objetivos pessoais", personalGoals);
  page += profileFieldHtml("limits", "Limites que devem ser respeitados", personalLimits) + "</section>";
  page += "<section class='section'><h2>Consentimentos</h2>";
  page += "<label class='check'><input type='checkbox' name='learn'" + String(profileLearningConsent ? " checked" : "") + ">Registrar contagens locais para adaptar o acompanhamento.</label>";
  page += "<label class='check'><input type='checkbox' name='predict'" + String(predictionConsent ? " checked" : "") + ">Mostrar alertas de possivel aumento de sobrecarga.</label>";
  page += "<label class='check'><input type='checkbox' name='cloud'" + String(cloudProfileConsent ? " checked" : "") + ">Permitir envio do perfil a uma IA externa quando configurada.</label>";
  page += "<p class='notice'>Os dados ficam na memoria local do dispositivo ate serem apagados. O portal usa HTTP na rede local. Registros em cartao SD ficam desativados por padrao.</p>";
  page += "<button type='submit'>Salvar perfil</button></section></form>";
  if (trustedPhone.length()) page += "<section class='section'><a href='tel:" + htmlEscape(trustedPhone) + "'><button>Ligar para " + htmlEscape(trustedName.length() ? trustedName : "contato") + "</button></a></section>";
  page += "<section class='section'><h2>Apagar dados</h2><form action='/erase' method='post'><button class='danger'>Apagar perfil e ciclo atual</button></form></section>";
  page += "</main></body></html>";

  client.println("HTTP/1.1 200 OK");
  client.println("Content-Type: text/html; charset=utf-8");
  client.println("Connection: close");
  client.print("Content-Length: ");
  client.println(page.length());
  client.println();
  client.print(page);
}

void saveProfileFromForm(const String &body) {
  preferredName = formField(body, "name");
  profileAge = formField(body, "age");
  profileNeuro = formField(body, "neuro");
  relevantConditions = formField(body, "conditions");
  communicationPreference = formField(body, "communication");
  sensoryNotes = formField(body, "sensory");
  earlySignals = formField(body, "early");
  worseningSignals = formField(body, "worse");
  knownTriggers = formField(body, "triggers");
  stressSituations = formField(body, "stress");
  helpfulStrategies = formField(body, "helps");
  harmfulStrategies = formField(body, "harms");
  calmingPhrase = formField(body, "calm");
  phrasesToAvoid = formField(body, "avoid");
  trustedName = formField(body, "trust_name");
  trustedPhone = formField(body, "trust_phone");
  treatmentNotes = formField(body, "treatment");
  routineNotes = formField(body, "routine");
  personalGoals = formField(body, "goals");
  personalLimits = formField(body, "limits");
  autonomyLevel = constrain(formField(body, "autonomy").toInt(), 1, 3);
  profileLearningConsent = formChecked(body, "learn");
  predictionConsent = formChecked(body, "predict");
  cloudProfileConsent = formChecked(body, "cloud");
  saveProfile();
}

void handleInputServer() {
  if (!inputServerStarted || aiBusy) return;
  WiFiClient client = inputServer.available();
  if (!client) return;

  String req = client.readStringUntil('\n');
  int contentLength = 0;
  uint32_t deadline = millis() + 1200;
  while (client.connected() && millis() < deadline) {
    if (!client.available()) {
      delay(2);
      continue;
    }
    String line = client.readStringUntil('\n');
    if (line.startsWith("Content-Length:")) contentLength = line.substring(15).toInt();
    if (line == "\r" || line.length() <= 1) break;
  }

  String body;
  if (contentLength > 0 && contentLength <= 7000) {
    body.reserve(contentLength);
    deadline = millis() + 2000;
    while ((int)body.length() < contentLength && millis() < deadline) {
      while (client.available() && (int)body.length() < contentLength) body += (char)client.read();
      delay(2);
    }
  }

  if (req.startsWith("POST /profile ")) {
    saveProfileFromForm(body);
    logInteraction("perfil_atualizado", "portal local");
    if (screen == 3) {
      lcd.fillScreen(BG);
      drawConfigScreen();
    }
    sendInputPage(client, "Perfil salvo na memoria local.");
    delay(20);
    client.stop();
    return;
  }
  if (req.startsWith("POST /erase ")) {
    erasePersonalData();
    screen = 2;
    lcd.fillScreen(BG);
    drawNeuralScreen();
    sendInputPage(client, "Perfil e ciclo apagados.");
    delay(20);
    client.stop();
    return;
  }

  int qStart = -1;
  if (qStart >= 0) {
    int start = qStart + 11;
    int end = req.indexOf(' ', start);
    String question = urlDecode(req.substring(start, end));
    if (question.length() > 280) question = question.substring(0, 280);
    lastQuestion = question;
    logSdLine("{\"event\":\"pergunta_web\",\"texto\":\"" + jsonEscape(question) + "\"}");
    aiBusy = true;
    aiStatus = "PENSANDO";
    aiAnswer = "PERGUNTA RECEBIDA. CONSULTANDO IA...";
    screen = 2;
    drawAiMetrics();
    drawAiAnswer();
    String prompt = "Responda esta pergunta do usuario de forma objetiva em portugues, maximo 500 caracteres: " + question;
    aiAnswer = askDeepSeek("custom", prompt);
    logSdLine("{\"event\":\"resposta_web\",\"texto\":\"" + jsonEscape(aiAnswer) + "\"}");
    aiStatus = String(DEEPSEEK_API_KEY).length() < 10 ? "LOCAL" : "DEEPSEEK";
    aiBusy = false;
    drawAiMetrics();
    drawAiAnswer();
    sendInputPage(client, "Resposta enviada para o display.");
  } else {
    sendInputPage(client, "");
  }
  delay(20);
  client.stop();
}

void drawConfigScreen() {
  drawHeader("PERFIL LOCAL");
  String identity = preferredName.length() ? preferredName : "CONFIGURE PELO ENDERECO IP";
  String contact = trustedName.length() ? trustedName : "SEM CONTATO CONFIGURADO";
  drawTextBox(8, 60, 304, 34, "TRATAMENTO", identity, CYAN);
  drawTextBox(8, 98, 304, 34, "PESSOA DE CONFIANCA", contact, AMBER);
  const char *guideLabels[] = {"GUIA CURTO", "GUIA NORMAL", "GUIA DETALHADO"};
  drawChoiceButton(8, 140, 148, 30, guideLabels[guidanceLevel], CYAN);
  drawChoiceButton(164, 140, 148, 30, predictionConsent ? "ALERTAS ON" : "ALERTAS OFF", predictionConsent ? GREEN : 0x7BEF);
  drawChoiceButton(8, 178, 148, 30, profileLearningConsent ? "APRENDER ON" : "APRENDER OFF", profileLearningConsent ? GREEN : 0x7BEF);
  drawChoiceButton(164, 178, 148, 30, cloudProfileConsent ? "NUVEM ON" : "NUVEM OFF", cloudProfileConsent ? AMBER : 0x7BEF);
  drawChoiceButton(8, 216, 148, 22, "CONFIGURAR WIFI", 0xB800);
  drawChoiceButton(164, 216, 148, 22, eraseConfirm ? "CONFIRMAR APAGAR" : "APAGAR DADOS", 0xD6BA);
}

void startSmartConfig() {
  smartConfigActive = true;
  Serial.println("WIFI: entering SmartConfig");
  WiFi.mode(WIFI_STA);
  WiFi.beginSmartConfig();
}

void handleConfigTouch(uint16_t x, uint16_t y) {
  bool changed = true;
  if (y >= 140 && y < 172 && x < 160) guidanceLevel = (guidanceLevel + 1) % 3;
  else if (y >= 140 && y < 172 && x >= 160) predictionConsent = !predictionConsent;
  else if (y >= 178 && y < 210 && x < 160) profileLearningConsent = !profileLearningConsent;
  else if (y >= 178 && y < 210 && x >= 160) cloudProfileConsent = !cloudProfileConsent;
  else if (y >= 214 && x < 160) {
    WiFi.disconnect(true, true);
    delay(200);
    startSmartConfig();
  } else if (y >= 214 && x >= 160) {
    if (eraseConfirm) erasePersonalData();
    else eraseConfirm = true;
  } else {
    changed = false;
  }
  if (changed) {
    if (!eraseConfirm || y < 214 || x < 160) saveProfile();
    lcd.fillScreen(BG);
    drawConfigScreen();
  }
}

void connectWifi() {
  prefs.begin("wifi", true);
  wifiSsid = prefs.getString("ssid", WIFI_SSID);
  wifiPass = prefs.getString("pass", WIFI_PASS);
  prefs.end();
  WiFi.persistent(true);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  Serial.println("WIFI: scanning");
  int networks = WiFi.scanNetworks();
  bool found = false;
  for (int i = 0; i < networks; i++) {
    if (WiFi.SSID(i) == wifiSsid) {
      found = true;
      Serial.print("WIFI: found configured ssid rssi=");
      Serial.println(WiFi.RSSI(i));
    }
  }
  if (!found) Serial.println("WIFI: configured ssid not found in scan");

  if (wifiSsid.length()) {
    Serial.println("WIFI: connecting to configured SSID");
    WiFi.begin(wifiSsid.c_str(), wifiPass.c_str());
  } else {
    Serial.println("WIFI: connecting to saved credentials");
    WiFi.begin();
  }
  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) {
    delay(500);
    Serial.print("WIFI: status=");
    Serial.println(WiFi.status());
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("WIFI: connected ip=");
    Serial.println(WiFi.localIP());
    startInputServer();
  } else {
    Serial.println("WIFI: connect failed");
    startSmartConfig();
  }
}

void scanWifi() {
  scanCount = WiFi.scanNetworks();
  lastScan = millis();
}

void saveWifiCredentials(const String &ssid, const String &pass) {
  prefs.begin("wifi", false);
  prefs.putString("ssid", ssid);
  prefs.putString("pass", pass);
  prefs.end();
  wifiSsid = ssid;
  wifiPass = pass;
}

void connectSelectedWifi() {
  if (!wifiSelectedSsid.length()) return;
  saveWifiCredentials(wifiSelectedSsid, wifiPassInput);
  wifiEntryMode = false;
  lcd.fillScreen(BG);
  drawHeader("WIFI");
  drawText(20, 104, "conectando...", AMBER, 2);
  WiFi.disconnect(true, false);
  delay(300);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.begin(wifiSsid.c_str(), wifiPass.c_str());
  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) {
    delay(400);
  }
  if (WiFi.status() == WL_CONNECTED) startInputServer();
  scanWifi();
  lcd.fillScreen(BG);
  previousScreen = 255;
}

void pressWifiKey(const String &group) {
  if (wifiPassInput.length() >= 64) return;
  uint32_t now = millis();
  if (wifiKeyGroup == group && now - wifiKeyTime < 900 && wifiPassInput.length()) {
    wifiKeyIndex = (wifiKeyIndex + 1) % group.length();
    wifiPassInput.setCharAt(wifiPassInput.length() - 1, group[wifiKeyIndex]);
  } else {
    wifiKeyGroup = group;
    wifiKeyIndex = 0;
    wifiPassInput += group[0];
  }
  wifiKeyTime = now;
}

void handleWifiTouch(uint16_t x, uint16_t y) {
  if (!wifiEntryMode) {
    if (scanCount < 0) {
      scanWifi();
      lcd.fillScreen(BG);
      previousScreen = 255;
      return;
    }
    for (int i = 0; i < min(scanCount, 5); i++) {
      int by = 126 + i * 21;
      if (x >= 8 && x <= 232 && y >= by && y < by + 18) {
        wifiSelectedSsid = WiFi.SSID(i);
        wifiPassInput = "";
        wifiKeyGroup = "";
        wifiEntryMode = true;
        lcd.fillScreen(BG);
        drawWifiScreen();
        return;
      }
    }
    return;
  }

  int col = -1;
  if (x >= 8 && x < 78) col = 0;
  else if (x >= 85 && x < 155) col = 1;
  else if (x >= 162 && x < 232) col = 2;
  if (col < 0) return;

  int row = -1;
  if (y >= 154 && y < 172) row = 0;
  else if (y >= 176 && y < 194) row = 1;
  else if (y >= 198 && y < 216) row = 2;
  else if (y >= 220 && y < 238) row = 3;
  if (row < 0) return;

  if (row == 0 && col == 0) pressWifiKey("1ABC");
  else if (row == 0 && col == 1) pressWifiKey("2DEF");
  else if (row == 0 && col == 2) pressWifiKey("3GHI");
  else if (row == 1 && col == 0) pressWifiKey("4JKL");
  else if (row == 1 && col == 1) pressWifiKey("5MNO");
  else if (row == 1 && col == 2) pressWifiKey("6PQRS");
  else if (row == 2 && col == 0) pressWifiKey("7TUV");
  else if (row == 2 && col == 1) pressWifiKey("8WXYZ");
  else if (row == 2 && col == 2) pressWifiKey("9.-_");
  else if (row == 3 && col == 0) {
    if (wifiPassInput.length()) wifiPassInput.remove(wifiPassInput.length() - 1);
    wifiKeyGroup = "";
  } else if (row == 3 && col == 1) {
    pressWifiKey("0");
  } else if (row == 3 && col == 2) {
    wifiKeyGroup = "";
    connectSelectedWifi();
    return;
  }
  drawWifiScreen();
}

void handleTouch() {
  uint16_t x, y;
  if (!readTouchPoint(x, y)) {
    touchWasDown = false;
    return;
  }
  if (touchWasDown) return;
  touchWasDown = true;
  if (millis() - lastTouch < 250) return;
  lastTouch = millis();

  if (screen == 2) {
    handleTamagotchiTouch(x, y);
    return;
  }

  if (y < 28) {
    screen = min((int)(x / (lcd.width() / 4)), 3);
    lcd.fillScreen(BG);
    previousScreen = 255;
    if (screen == 1) scanWifi();
    return;
  }

  if (screen == 1) {
    handleWifiTouch(x, y);
    return;
  }

  if (screen == 3) {
    handleConfigTouch(x, y);
  }
}

void setup() {
  pinMode(LDR_PIN, INPUT);
  pinMode(LED_R, OUTPUT);
  pinMode(LED_G, OUTPUT);
  pinMode(LED_B, OUTPUT);
  pinMode(TFT_BL, OUTPUT);
  digitalWrite(TFT_BL, HIGH);
  Serial.begin(115200);
  tftSPI.begin(TFT_SCLK, TFT_MISO, TFT_MOSI, TFT_CS);
  touchSPI.begin(TOUCH_SCLK, TOUCH_MISO, TOUCH_MOSI, TOUCH_CS);
  pinMode(TOUCH_CS, OUTPUT);
  pinMode(TOUCH_IRQ, INPUT);
  digitalWrite(TOUCH_CS, HIGH);
  lcd.begin();
  lcd.setRotation(1);
  loadProfile();
  loadCycle();
  loadTouchCalibration();
  prefs.begin("touch", true);
  uint8_t calVersion = prefs.getUChar("ver", 0);
  prefs.end();
  if (FORCE_TOUCH_CALIBRATION || calVersion != TOUCH_CAL_VERSION) {
    runTouchCalibration();
    prefs.begin("touch", false);
    prefs.putBool("done", true);
    prefs.putUChar("ver", TOUCH_CAL_VERSION);
    prefs.end();
  }
  tryInitSd();
  lcd.fillScreen(BG);
  drawText(34, 110, "ACOMPANHANTE", CYAN, 2);
  drawText(54, 138, "iniciando WiFi...", MUTED);
  connectWifi();
  fpsMark = millis();
}

void loop() {
  handleTouch();
  if (smartConfigActive && WiFi.smartConfigDone()) {
    smartConfigActive = false;
    WiFi.stopSmartConfig();
    if (WiFi.status() == WL_CONNECTED) startInputServer();
  }
  handleInputServer();

  if (WiFi.status() == WL_CONNECTED) setStatusLed(0, 80, 16);
  else setStatusLed(90, 45, 0);

  if (millis() - lastScan > 30000 && screen == 1) scanWifi();

  frames++;
  if (millis() - fpsMark >= 1000) {
    fps = frames;
    frames = 0;
    fpsMark = millis();
  }

  if (previousScreen != screen) {
    lcd.fillScreen(BG);
    previousScreen = screen;
    lastFullClear = millis();
    if (screen == 0) drawOverview();
    if (screen == 1) drawWifiScreen();
    if (screen == 2) drawNeuralScreen();
    if (screen == 3) drawConfigScreen();
    return;
  }

  if (screen != 2 && millis() - lastFrame > 8000) lastFrame = millis();
}
