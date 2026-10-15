#include <Arduino.h>
#include <SPI.h>
#include <Preferences.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ILI9341.h>
#include <XPT2046_Touchscreen.h>
#include <FS.h>
#include <SD.h>
#include "esp_bt.h"
#include "esp_bt_main.h"
#include "esp_bt_device.h"
#include "esp_gap_bt_api.h"
#include "esp_a2dp_api.h"
#include "esp_hf_ag_api.h"
#include "esp_wifi.h"

// Miniatura do kiosk CONTROL: uma acao de cada vez, mesma lingua.

namespace Pins {
constexpr int tftSclk = 14, tftMosi = 13, tftMiso = 12, tftDc = 2, tftCs = 15, backlight = 21;
constexpr int touchSclk = 25, touchMosi = 32, touchMiso = 39, touchCs = 33, touchIrq = 36, speaker = 26;
constexpr int sdSck = 18, sdMiso = 19, sdMosi = 23, sdCs = 5;
}

SPIClass tftSpi(VSPI), touchSpi(HSPI);
Adafruit_ILI9341 lcd(&tftSpi, Pins::tftDc, Pins::tftCs, -1);
XPT2046_Touchscreen touch(Pins::touchCs); // sem IRQ: GPIO36 trava isrWake e o toque morre
Preferences prefs;

constexpr const char* LAN_CTRL = "http://192.168.15.4:8788/cyd";
constexpr const char* LAN_ACK = "http://192.168.15.4:8788/cyd/ack";
constexpr const char* LAN_ACT = "http://192.168.15.4:8788/cyd/act";
constexpr const char* LAN_ASK = "http://192.168.15.4:8788/cyd/ask";
constexpr const char* LAN_DIA = "http://192.168.15.4:8788/cyd/diary";
constexpr const char* LAN_LIS = "http://192.168.15.4:8788/cyd/listen";
constexpr const char* LAN_VOX = "http://192.168.15.4:8788/cyd/voice.pcm";
constexpr const char* LAN_STT = "http://192.168.15.4:8788/cyd/stt";
constexpr const char* TS_CTRL = "https://cpqd8nr2jg4.taile5dcde.ts.net/cyd";
constexpr const char* TS_ACK = "https://cpqd8nr2jg4.taile5dcde.ts.net/cyd/ack";
constexpr const char* TS_ACT = "https://cpqd8nr2jg4.taile5dcde.ts.net/cyd/act";
constexpr const char* TS_ASK = "https://cpqd8nr2jg4.taile5dcde.ts.net/cyd/ask";
constexpr const char* TS_DIA = "https://cpqd8nr2jg4.taile5dcde.ts.net/cyd/diary";
constexpr const char* TS_LIS = "https://cpqd8nr2jg4.taile5dcde.ts.net/cyd/listen";
constexpr const char* TS_VOX = "https://cpqd8nr2jg4.taile5dcde.ts.net/cyd/voice.pcm";
constexpr const char* TS_STT = "https://cpqd8nr2jg4.taile5dcde.ts.net/cyd/stt";
constexpr const char* CLOUD_CTRL = "https://control.ch8ai.com.br/cyd";
constexpr const char* CLOUD_ACK = "https://control.ch8ai.com.br/cyd/ack";
constexpr const char* CLOUD_ACT = "https://control.ch8ai.com.br/cyd/act";
constexpr const char* CLOUD_ASK = "https://control.ch8ai.com.br/cyd/ask";
constexpr const char* CLOUD_LIS = "https://control.ch8ai.com.br/cyd/listen";
constexpr const char* WIFI_SSID = "";
constexpr const char* WIFI_PASS = "";

constexpr uint16_t BG = 0x20C2, PANEL = 0x3103, LINE = 0x51C4, SHADOW = 0x1880;
constexpr uint16_t YELLOW = 0xFC40, PAPER = 0xE6F9, WHITE = 0xFFFF;
constexpr uint16_t MUTED = 0x8208, AMBER = 0xFBC0, RED = 0xC0E3, INK = 0x1880;
constexpr uint16_t BLUE = 0x5C9A, PINK = 0xC3B0, CARD = 0x3943, NAV = 0x1880;

enum class Screen { Home, Fila, Agenda, Frota, Nums, Agent, Item, Ask, AskType, Talk, Settings, Diary, Networks, Password, Calibrate, BtList };
Screen screen = Screen::Home;
Screen listScreen = Screen::Fila;

String ssid, pass, ctrlBody, brief, nextEvent, health = "OFF", hoje, futuro, foco, mit, ancora, consel;
String askQ, askA, askAg, typedAsk;
bool askPending = false;
uint8_t viaHop = 0;
uint32_t skipLanUntil = 0;
int alerts = 0, tasksN = 0, agentsN = 0, working = 0, down = 0;
int cursor = 0, listCount = 0, listScroll = 0, dragY0 = 0, scroll0 = 0, tapX = 0, tapY = 0;
String listA[8], listB[8], listC[8], listId[8];
char listK[8] = {};
bool dragged = false;
constexpr int kRow = 42, kListTop = 40, kListH = 160;

String agName[24], agAct[24], agHead[24], agRole[24], agShort[24], agTeam[24];
bool agentBusy[24] = {};
int agLoad[24] = {};
int agTotal = 0, agPage = 0, agCursor = 0;
int crewPhase = 0;
uint32_t lastAnim = 0;
int flFrom[10] = {}, flTo[10] = {}, flT[10] = {};
bool connecting = false, fetching = false, keyboardUpper = true, touchHeld = false, fromAgent = false, fromTalk = false;
bool vozPlaca = false, btOn = false, btLinked = false, btScanning = false;
char btPeer[24] = "";
struct BtDev { char name[24]; esp_bd_addr_t addr; };
BtDev btDevs[8];
int btCount = 0, btPage = 0;
uint32_t connectStarted = 0, lastFetch = 0;
int kpi[8] = {};
String coName[6];
int coProj[6] = {}, coMeet[6] = {}, coOpen[6] = {}, coDone[6] = {};
int coCount = 0;
String dyLab[5];
int dyMeet[5] = {}, dyDone[5] = {};
int dyCount = 0;
int numPage = 0;
int networkCount = 0, networkPage = 0;
String pendingSsid, typedPass;
const char kKeysUpper[] = "1234567890QWERTYUIOPASDFGHJKL<ZXCVBNM._";
const char kKeysLower[] = "1234567890qwertyuiopasdfghjkl<zxcvbnm._";
int touchL = 300, touchR = 3900, touchT = 300, touchB = 3900, touchSwap = 0;
int calStep = 0, calX[5] = {}, calY[5] = {}, calN = 0, calXs[20] = {}, calYs[20] = {};
int tapDownX = 0, tapDownY = 0;
bool waitRelease = false;
constexpr int kCalX[5] = {36, 284, 284, 36, 160};
constexpr int kCalY[5] = {36, 36, 204, 204, 120};

String nowTitle, nowWho, nowId, nowAg;
char nowK = 0;
String skipIds;

String clockDate = "2026-09-08";
int clockSec = 12 * 3600;
uint32_t clockBaseMs = 0;
bool sdOk = false;
uint32_t sdRetryAt = 0;
int diaryDayLines = 0;
String diaryLines[10];
int diaryN = 0;
String diaryPend[6];
int diaryPendN = 0;
uint32_t lastDiaryNet = 0;

void beep(int hz = 1200, int ms = 30) { tone(Pins::speaker, hz, ms); }
void diaryLog(const char* kind, const String& detail);
void setClockFromStamp(const String& stamp);

uint16_t textW(const String& s, uint8_t z = 1) {
  int16_t x, y; uint16_t w, h;
  lcd.setTextSize(z); lcd.getTextBounds(s, 0, 0, &x, &y, &w, &h);
  return w;
}
void center(const String& s, int x, int y, uint8_t z, uint16_t c) {
  lcd.setTextSize(z); lcd.setTextColor(c);
  lcd.setCursor(x - textW(s, z) / 2, y); lcd.print(s);
}
void wrap(const String& s, int x, int y, int width, int lineH, uint16_t color, uint8_t size = 1, int maxLines = 4) {
  lcd.setTextColor(color); lcd.setTextSize(size);
  String word; int cx = x, cy = y, lines = 1;
  for (size_t i = 0; i <= s.length(); i++) {
    char ch = i < s.length() ? s[i] : '\0';
    if (ch != ' ' && ch != '\0') { word += ch; continue; }
    int ww = textW(word + " ", size);
    if (cx + ww > x + width) { cx = x; cy += lineH; if (++lines > maxLines) return; }
    lcd.setCursor(cx, cy); lcd.print(word); cx += ww; word = "";
    if (ch == '\0') break;
  }
}
void button(int x, int y, int w, int h, const String& s, uint16_t bg, uint16_t fg = INK) {
  uint16_t col = (bg == YELLOW) ? YELLOW : (bg == RED) ? RED : PAPER;
  if (fg == MUTED) col = MUTED;
  center(s, x + w / 2, y + (h > 22 ? (h - 8) / 2 : 7), 1, col);
  if (bg == YELLOW) lcd.drawFastHLine(x + 10, y + h - 5, w - 20, YELLOW);
}
void cardBox(int x, int y, int w, int h, uint16_t accent) {
  if (accent) lcd.fillRect(x, y + 4, 3, h - 8, accent);
}
void lamp(int x, int y, uint16_t col) {
  lcd.fillCircle(x + 3, y + 3, 3, col);
}
void tag(int x, int y, int w, int h, const String& s, uint16_t bg, uint16_t fg) {
  center(s, x + w / 2, y + (h - 8) / 2, 1, fg == INK ? YELLOW : fg);
}
uint16_t teamColor(const String& t) {
  if (t == "chief") return YELLOW;
  return MUTED;
}
uint16_t kindColor(char k) {
  if (k == 'S') return RED;
  return YELLOW;
}
bool hit(int x, int y, int bx, int by, int w, int h) {
  return x >= bx && x < bx + w && y >= by && y < by + h;
}

char kindOf(const String& title, const String& id, char src) {
  if (id.startsWith("out-")) return 'O';
  String t = title;
  t.toUpperCase();
  if (t.indexOf("RSVP") >= 0 || t.indexOf("CONVITE") >= 0 || t.indexOf("ACEITAR") >= 0) return 'R';
  if (src == 'E') return 'E';
  if (src == 'T') return 'T';
  if (src == 'S') return 'S';
  return 'M';
}
const char* kindLabel(char k) {
  if (k == 'O') return "enviar";
  if (k == 'R') return "rsvp";
  if (k == 'T') return "tarefa";
  if (k == 'E') return "agenda";
  if (k == 'S') return "host";
  return "recado";
}
bool skipped(const String& id) {
  return id.length() && skipIds.indexOf("|" + id + "|") >= 0;
}
void skip(const String& id) {
  if (!id.length()) return;
  skipIds += "|" + id + "|";
  if (skipIds.length() > 360) skipIds = skipIds.substring(skipIds.length() - 240);
}

static volatile int btTone = 0;
static int16_t btPlay[16000];
static volatile int btPlayN = 0, btPlayI = 0;
static int16_t recBuf[6000];
static volatile int recN = 0;

static void btAdd(const char* name, uint8_t* addr) {
  if (!name || !name[0] || btCount >= 8) return;
  for (int i = 0; i < btCount; i++) if (memcmp(btDevs[i].addr, addr, 6) == 0) return;
  strncpy(btDevs[btCount].name, name, 23);
  btDevs[btCount].name[23] = 0;
  memcpy(btDevs[btCount].addr, addr, 6);
  btCount++;
}

extern "C" void gap_cb(esp_bt_gap_cb_event_t ev, esp_bt_gap_cb_param_t* p) {
  if (ev == ESP_BT_GAP_DISC_RES_EVT) {
    char name[24] = {0};
    uint8_t* eir = nullptr;
    for (int i = 0; i < p->disc_res.num_prop; i++) {
      esp_bt_gap_dev_prop_t* pr = &p->disc_res.prop[i];
      if (pr->type == ESP_BT_GAP_DEV_PROP_BDNAME && pr->val) {
        int n = pr->len < 23 ? pr->len : 23;
        memcpy(name, pr->val, n);
        name[n] = 0;
      }
      if (pr->type == ESP_BT_GAP_DEV_PROP_EIR) eir = (uint8_t*)pr->val;
    }
    if (!name[0] && eir) {
      uint8_t len = 0;
      uint8_t* n = esp_bt_gap_resolve_eir_data(eir, ESP_BT_EIR_TYPE_CMPL_LOCAL_NAME, &len);
      if (!n) n = esp_bt_gap_resolve_eir_data(eir, ESP_BT_EIR_TYPE_SHORT_LOCAL_NAME, &len);
      if (n && len) {
        if (len > 23) len = 23;
        memcpy(name, n, len);
        name[len] = 0;
      }
    }
    if (name[0]) btAdd(name, p->disc_res.bda);
  }
  if (ev == ESP_BT_GAP_DISC_STATE_CHANGED_EVT &&
      p->disc_st_chg.state == ESP_BT_GAP_DISCOVERY_STOPPED) {
    btScanning = false;
  }
}

extern "C" void a2d_cb(esp_a2d_cb_event_t ev, esp_a2d_cb_param_t* p) {
  if (ev == ESP_A2D_CONNECTION_STATE_EVT) {
    btLinked = (p->conn_stat.state == ESP_A2D_CONNECTION_STATE_CONNECTED);
    if (btLinked) {
      btTone = 20000;
      esp_a2d_media_ctrl(ESP_A2D_MEDIA_CTRL_START);
    }
  }
}

extern "C" int32_t a2d_pcm(uint8_t* data, int32_t len) {
  int16_t* s = (int16_t*)data;
  int n = len / 2;
  int frames = n / 2;
  if (frames < 1) frames = n;
  for (int f = 0; f < frames; f++) {
    int16_t v = 0;
    if (btPlayN > 0) {
      int src = (int)((int32_t)btPlayI * 16000L / 44100L);
      if (src < btPlayN) v = btPlay[src];
      btPlayI++;
    } else if (btTone > 0) {
      v = (f & 8) ? 5000 : -5000;
      btTone--;
    }
    if (n == frames) s[f] = v;
    else {
      s[f * 2] = v;
      s[f * 2 + 1] = v;
    }
  }
  return len;
}

extern "C" void hf_in(const uint8_t* buf, uint32_t len) {
  const int16_t* s = (const int16_t*)buf;
  int n = (int)(len / 2);
  for (int i = 0; i < n && recN < 6000; i++) recBuf[recN++] = s[i];
}

extern "C" uint32_t hf_out(uint8_t* buf, uint32_t len) {
  memset(buf, 0, len);
  return len;
}

extern "C" void hf_cb(esp_hf_cb_event_t, esp_hf_cb_param_t*) {}

void audioBtStart() {
  if (btOn) return;
  esp_bt_controller_mem_release(ESP_BT_MODE_BLE);
  esp_bt_controller_config_t cfg = BT_CONTROLLER_INIT_CONFIG_DEFAULT();
  if (esp_bt_controller_init(&cfg) != ESP_OK) return;
  if (esp_bt_controller_enable(ESP_BT_MODE_CLASSIC_BT) != ESP_OK) return;
  if (esp_bluedroid_init() != ESP_OK) return;
  if (esp_bluedroid_enable() != ESP_OK) return;
  esp_bt_gap_register_callback(gap_cb);
  esp_bt_gap_set_device_name("CONTROL");
  esp_bt_gap_set_scan_mode(ESP_BT_CONNECTABLE, ESP_BT_GENERAL_DISCOVERABLE);
  esp_a2d_register_callback(a2d_cb);
  esp_a2d_source_init();
  esp_a2d_source_register_data_callback(a2d_pcm);
  esp_hf_ag_register_callback(hf_cb);
  esp_hf_ag_init();
  esp_hf_ag_register_data_callback(hf_in, hf_out);
  esp_wifi_set_ps(WIFI_PS_MIN_MODEM);
  btOn = true;
  Serial.println("BT CONTROL visivel");
}

void btScan() {
  btCount = 0;
  btPage = 0;
  btScanning = true;
  if (!btOn) audioBtStart();
  if (btOn) esp_bt_gap_start_discovery(ESP_BT_INQ_MODE_GENERAL_INQUIRY, 8, 0);
}

void header(const char* section);
void fetchBtVoice();
void drawBtList();
void openBtList() {
  vozPlaca = true;
  prefs.putBool("vozPlaca", true);
  btScan();
  drawBtList();
}

void drawBtList() {
  header("fone na placa");
  lcd.setTextColor(MUTED); lcd.setTextSize(1); lcd.setCursor(12, 40);
  lcd.print(btLinked ? btPeer : "pareie CONTROL no fone");
  if (btScanning && btCount == 0) wrap("Procurando fones...", 12, 70, 296, 16, PAPER, 1, 2);
  int start = btPage * 4;
  for (int row = 0; row < 4; row++) {
    int idx = start + row;
    if (idx >= btCount) break;
    button(10, 58 + row * 32, 300, 28, btDevs[idx].name, PANEL, PAPER);
  }
  button(10, 204, 90, 28, "voltar", PANEL, MUTED);
  button(110, 204, 95, 28, "buscar", YELLOW);
  button(215, 204, 95, 28, "mais", PANEL, PAPER);
  screen = Screen::BtList;
}

void header(const char* section) {
  lcd.fillScreen(BG);
  lcd.fillCircle(17, 16, 9, YELLOW);
  center("C", 17, 11, 2, INK);
  lcd.setTextColor(PAPER); lcd.setTextSize(2); lcd.setCursor(32, 4); lcd.print("CONTROL");
  lcd.setTextSize(1); lcd.setTextColor(MUTED); lcd.setCursor(32, 22);
  lcd.print(section);
  lcd.drawFastHLine(8, 32, 304, MUTED);
  uint16_t viaCol = viaHop == 0 ? MUTED : YELLOW;
  lamp(248, 12, viaCol);
  uint16_t hc = health == "OLD" ? AMBER : health == "WARN" ? RED : health == "OK" ? YELLOW : MUTED;
  lamp(264, 12, hc);
  lcd.setTextColor(MUTED); lcd.setCursor(276, 13);
  lcd.print(viaHop == 1 ? "lan" : viaHop == 2 ? "ts" : "net");
}

void openFila();
void openAgenda();
void openFrota();
void openNums();
void openTalk();
void drawTalk();

constexpr int kNavX[5] = {3, 67, 131, 195, 257};
constexpr int kNavW[5] = {62, 62, 62, 60, 60};

void drawNav(int tab) {
  const char* labs[5] = {"fila", "hoje", "frota", "num", "guia"};
  lcd.drawFastHLine(8, 202, 304, MUTED);
  for (int i = 0; i < 5; i++) {
    bool on = i == tab;
    center(labs[i], kNavX[i] + kNavW[i] / 2, 214, 1, on ? YELLOW : MUTED);
    if (on) lcd.drawFastHLine(kNavX[i] + 10, 230, kNavW[i] - 20, YELLOW);
  }
}

bool hitNav(int x, int y, int tab) {
  return y >= 204 && hit(x, y, kNavX[tab], 204, kNavW[tab], 32);
}

bool tapNav(int x, int y) {
  if (y < 204) return false;
  if (hitNav(x, y, 0)) { openFila(); return true; }
  if (hitNav(x, y, 1)) { openAgenda(); return true; }
  if (hitNav(x, y, 2)) { openFrota(); return true; }
  if (hitNav(x, y, 3)) { openNums(); return true; }
  if (hitNav(x, y, 4)) { openTalk(); return true; }
  return false;
}

String field(const String& body, const String& key) {
  String m = key + "=";
  int a = body.indexOf("\n" + m);
  if (a < 0) {
    if (body.startsWith(m)) a = 0;
    else return "";
  } else a += 1;
  a += m.length();
  int e = body.indexOf('\n', a);
  if (e < 0) e = body.length();
  String v = body.substring(a, e);
  v.trim();
  return v;
}
String pipe(const String& s, int idx) {
  int start = 0;
  for (int i = 0; i < idx; i++) {
    int p = s.indexOf('|', start);
    if (p < 0) return "";
    start = p + 1;
  }
  int p = s.indexOf('|', start);
  return p < 0 ? s.substring(start) : s.substring(start, p);
}

void pickNow() {
  nowK = 0; nowTitle = ""; nowWho = ""; nowId = ""; nowAg = "";
  for (int i = 1; i <= 8 && !nowK; i++) {
    String row = field(ctrlBody, "IN" + String(i));
    if (!row.length()) break;
    String id = pipe(row, 3);
    if (skipped(id)) continue;
    nowAg = pipe(row, 0); nowTitle = pipe(row, 1); nowWho = pipe(row, 2); nowId = id;
    nowK = kindOf(nowTitle, nowId, 'M');
  }
  for (int i = 1; i <= 8 && !nowK; i++) {
    String row = field(ctrlBody, "TK" + String(i));
    if (!row.length()) break;
    String id = pipe(row, 3);
    if (skipped(id)) continue;
    nowAg = pipe(row, 0); nowTitle = pipe(row, 1); nowWho = pipe(row, 2); nowId = id;
    nowK = kindOf(nowTitle, nowId, 'T');
  }
}

void parseCtrl(const String& body) {
  if (!body.startsWith("CTRL/1")) return;
  ctrlBody = body;
  health = field(body, "HEALTH");
  if (!health.length()) health = "OK";
  alerts = field(body, "ALERTS").toInt();
  tasksN = field(body, "TASKS").toInt();
  agentsN = field(body, "AGENTS").toInt();
  working = field(body, "WORKING").toInt();
  down = field(body, "DOWN").toInt();
  nextEvent = field(body, "NEXT");
  brief = field(body, "BRIEF");
  hoje = field(body, "HOJE");
  futuro = field(body, "FUTURO");
  foco = field(body, "FOCO");
  if (!foco.length()) foco = brief;
  mit = field(body, "MIT");
  ancora = field(body, "ANC");
  consel = field(body, "CON");
  String askRow = field(body, "ASK");
  if (askRow.length() && pipe(askRow, 0) == askAg) {
    String ans = pipe(askRow, 2);
    if (ans.length() && ans != "consultando CONTROL...") {
      ans.replace("*", "");
      ans.replace("_", "");
      ans.replace("`", "");
      ans.replace("#", "");
      if (askA != ans) diaryLog("RESP", ans);
      askA = ans;
      askPending = false;
      if (vozPlaca && btLinked) fetchBtVoice();
    }
  }
  String stamp = field(body, "STAMP");
  if (stamp.length()) setClockFromStamp(stamp);
  String via = field(body, "VIA");
  if (via == "LAN") viaHop = 1;
  else if (via == "TS" || via == "TAIL") viaHop = 2;
  else if (via == "NET" || via == "CLOUD") viaHop = 0;
  agTotal = 0;
  for (int i = 0; i < 24; i++) {
    String row = field(body, "AG" + String(i + 1));
    if (!row.length()) break;
    agName[agTotal] = pipe(row, 0);
    agentBusy[agTotal] = pipe(row, 1) == "RUN";
    agAct[agTotal] = pipe(row, 2);
    agLoad[agTotal] = pipe(row, 3).toInt();
    agHead[agTotal] = pipe(row, 4);
    agRole[agTotal] = pipe(row, 5);
    agShort[agTotal] = pipe(row, 6);
    agTeam[agTotal] = pipe(row, 7);
    if (!agShort[agTotal].length()) agShort[agTotal] = agName[agTotal].substring(0, 3);
    if (!agTeam[agTotal].length()) agTeam[agTotal] = "ops";
    agTotal++;
  }
  String kp = field(body, "KPI");
  for (int i = 0; i < 8; i++) kpi[i] = pipe(kp, i).toInt();
  coCount = 0;
  for (int i = 0; i < 6; i++) {
    String row = field(body, "CO" + String(i + 1));
    if (!row.length()) break;
    coName[coCount] = pipe(row, 0);
    coProj[coCount] = pipe(row, 1).toInt();
    coMeet[coCount] = pipe(row, 2).toInt();
    coOpen[coCount] = pipe(row, 3).toInt();
    coDone[coCount] = pipe(row, 4).toInt();
    coCount++;
  }
  dyCount = 0;
  for (int i = 0; i < 5; i++) {
    String row = field(body, "DY" + String(i + 1));
    if (!row.length()) break;
    dyLab[dyCount] = pipe(row, 0);
    dyMeet[dyCount] = pipe(row, 1).toInt();
    dyDone[dyCount] = pipe(row, 2).toInt();
    dyCount++;
  }
  pickNow();
  prefs.putString("ctrl", body.substring(0, 2000));
}

bool httpGet(const char* url, bool tls, String& body) {
  HTTPClient http;
  http.setConnectTimeout(tls ? 5000 : 2000);
  http.setTimeout(tls ? 10000 : 4000);
  int code = 0;
  if (tls) {
    WiFiClientSecure c;
    c.setInsecure();
    if (!http.begin(c, url)) return false;
    code = http.GET();
    if (code == 200) body = http.getString();
    http.end();
  } else {
    WiFiClient c;
    if (!http.begin(c, url)) return false;
    code = http.GET();
    if (code == 200) body = http.getString();
    http.end();
  }
  return code == 200;
}

bool fetchCtrl() {
  if (WiFi.status() != WL_CONNECTED) return false;
  fetching = true;
  String body;
  bool ok = false;
  if (millis() >= skipLanUntil) {
    ok = httpGet(LAN_CTRL, false, body) && body.startsWith("CTRL/1");
    if (ok) viaHop = 1;
    else skipLanUntil = millis() + 60000UL;
  }
  if (!ok) {
    ok = httpGet(TS_CTRL, true, body) && body.startsWith("CTRL/1");
    if (ok) viaHop = 2;
  }
  if (!ok) {
    ok = httpGet(CLOUD_CTRL, true, body) && body.startsWith("CTRL/1");
    if (ok) viaHop = 0;
  }
  fetching = false;
  lastFetch = millis();
  Serial.printf("fetch hop=%u ok=%d\n", viaHop, ok);
  if (!ok) return false;
  auto strip = [](const String& b) {
    int a = b.indexOf("\nSTAMP=");
    if (a < 0) return b;
    int e = b.indexOf('\n', a + 1);
    return e < 0 ? b.substring(0, a) : b.substring(0, a) + b.substring(e);
  };
  if (ctrlBody.length() && strip(body) == strip(ctrlBody)) return false;
  parseCtrl(body);
  return true;
}

void postJson(const char* url, const String& payload, bool tls) {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  http.setConnectTimeout(tls ? 4000 : 2000);
  http.setTimeout(tls ? 8000 : 4000);
  if (tls) {
    WiFiClientSecure c;
    c.setInsecure();
    if (!http.begin(c, url)) return;
    http.addHeader("Content-Type", "application/json");
    http.POST(payload);
    http.end();
  } else {
    WiFiClient c;
    if (!http.begin(c, url)) return;
    http.addHeader("Content-Type", "application/json");
    http.POST(payload);
    http.end();
  }
}

void sendAsk(const String& agent, const String& q);
void fetchBtVoice();

void postHop(const String& payload, const char* lan, const char* ts, const char* cloud) {
  if (viaHop == 1) postJson(lan, payload, false);
  else if (viaHop == 2) postJson(ts, payload, true);
  else postJson(cloud, payload, true);
}

void fetchBtVoice() {
  if (!vozPlaca || !btLinked) return;
  const char* url = viaHop == 1 ? LAN_VOX : viaHop == 2 ? TS_VOX : "";
  if (!url[0]) return;
  HTTPClient http;
  http.setConnectTimeout(viaHop == 1 ? 2000 : 4000);
  http.setTimeout(8000);
  bool ok = false;
  if (viaHop == 1) {
    WiFiClient c;
    ok = http.begin(c, url);
  } else {
    WiFiClientSecure s;
    s.setInsecure();
    ok = http.begin(s, url);
  }
  if (!ok) return;
  int code = http.GET();
  if (code == 200) {
    int n = http.getSize();
    if (n < 0) n = 48000;
    if (n > (int)sizeof(btPlay)) n = sizeof(btPlay);
    int got = http.getStream().readBytes((uint8_t*)btPlay, n);
    btPlayN = got / 2;
    btPlayI = 0;
  }
  http.end();
}

String postRaw(const char* url, uint8_t* data, int n, bool tls) {
  String out;
  HTTPClient http;
  http.setConnectTimeout(tls ? 4000 : 2000);
  http.setTimeout(tls ? 16000 : 14000);
  bool ok = false;
  if (tls) {
    WiFiClientSecure s;
    s.setInsecure();
    ok = http.begin(s, url);
  } else {
    WiFiClient c;
    ok = http.begin(c, url);
  }
  if (!ok) return out;
  http.addHeader("Content-Type", "application/octet-stream");
  http.POST(data, n);
  out = http.getString();
  http.end();
  return out;
}

String postJsonRet(const char* url, const String& payload, bool tls) {
  String out;
  if (WiFi.status() != WL_CONNECTED) return out;
  HTTPClient http;
  http.setConnectTimeout(tls ? 4000 : 2000);
  http.setTimeout(tls ? 20000 : 18000);
  if (tls) {
    WiFiClientSecure c;
    c.setInsecure();
    if (!http.begin(c, url)) return out;
    http.addHeader("Content-Type", "application/json");
    http.POST(payload);
    out = http.getString();
    http.end();
  } else {
    WiFiClient c;
    if (!http.begin(c, url)) return out;
    http.addHeader("Content-Type", "application/json");
    http.POST(payload);
    out = http.getString();
    http.end();
  }
  return out;
}

String jsonTextField(const String& raw) {
  int i = raw.indexOf("\"text\"");
  if (i < 0) return "";
  i = raw.indexOf(':', i);
  if (i < 0) return "";
  i = raw.indexOf('"', i);
  if (i < 0) return "";
  i += 1;
  String o;
  for (; i < raw.length(); i++) {
    char ch = raw[i];
    if (ch == '"') break;
    if (ch == '\\' && i + 1 < raw.length()) { o += raw[++i]; continue; }
    o += ch;
  }
  return o;
}

void listenVoice() {
  if (vozPlaca && btLinked) {
    recN = 0;
    btTone = 12000;
    askAg = "orquestrador";
    askA = "Fale no fone da placa agora.";
    drawTalk();
    uint32_t t0 = millis();
    while (millis() - t0 < 6500) delay(30);
    if (recN < 600) {
      askA = "Nao captei no fone. Escreva, ou escolha computador.";
      drawTalk();
      return;
    }
    String raw;
    if (viaHop == 1) raw = postRaw(LAN_STT, (uint8_t*)recBuf, recN * 2, false);
    else if (viaHop == 2) raw = postRaw(TS_STT, (uint8_t*)recBuf, recN * 2, true);
    String heard = jsonTextField(raw);
    if (!heard.length()) {
      askA = "Nao entendi. Escreva a pergunta.";
      drawTalk();
      return;
    }
    askQ = heard;
    askA = "consultando CONTROL...";
    sendAsk(askAg, heard);
    drawTalk();
    return;
  }
  askAg = "orquestrador";
  askQ = "voz";
  askA = "Ouvindo o fone Bluetooth deste PC...";
  drawTalk();
  String raw;
  if (viaHop == 1) raw = postJsonRet(LAN_LIS, "{}", false);
  else if (viaHop == 2) raw = postJsonRet(TS_LIS, "{}", true);
  else raw = postJsonRet(CLOUD_LIS, "{}", true);
  String heard = jsonTextField(raw);
  if (!heard.length()) {
    askA = "Nao ouvi. Pareie o fone no Windows e fale de novo.";
    drawTalk();
    return;
  }
  askQ = heard;
  askA = "consultando CONTROL...";
  sendAsk(askAg, heard);
  drawTalk();
}

void diaryLog(const char* kind, const String& detail);

void sendKind(const String& id, const char* kind, const char* extra = "") {
  if (!id.length()) return;
  String p = "{\"id\":\"";
  p += id;
  p += "\",\"kind\":\"";
  p += kind;
  p += "\"";
  if (extra && extra[0]) { p += ","; p += extra; }
  p += "}";
  postHop(p, LAN_ACT, TS_ACT, CLOUD_ACT);
  diaryLog("ACAO", String(kind) + " " + id);
}

void jsonEsc(const String& s, String& out) {
  for (size_t i = 0; i < s.length(); i++) {
    char ch = s[i];
    if (ch == '"' || ch == '\\') out += '\\';
    if (ch >= 32) out += ch;
  }
}

void setClockFromStamp(const String& stamp) {
  if (stamp.length() < 19) return;
  clockDate = stamp.substring(0, 10);
  int h = stamp.substring(11, 13).toInt();
  int m = stamp.substring(14, 16).toInt();
  int s = stamp.substring(17, 19).toInt();
  clockSec = h * 3600 + m * 60 + s;
  clockBaseMs = millis();
}

String nowClock() {
  int t = clockSec + (int)((millis() - clockBaseMs) / 1000UL);
  t %= 86400;
  if (t < 0) t += 86400;
  char buf[12];
  snprintf(buf, sizeof(buf), " %02d:%02d:%02d", t / 3600, (t % 3600) / 60, t % 60);
  return clockDate + buf;
}

void restoreTouchSpi() {
  digitalWrite(Pins::sdCs, HIGH);
  pinMode(Pins::touchCs, OUTPUT);
  digitalWrite(Pins::touchCs, HIGH);
  touchSpi.end();
  touchSpi.begin(Pins::touchSclk, Pins::touchMiso, Pins::touchMosi, Pins::touchCs);
  touch.begin(touchSpi);
  touch.setRotation(1);
}

bool diaryMount() {
  pinMode(Pins::sdCs, OUTPUT);
  digitalWrite(Pins::sdCs, HIGH);
  digitalWrite(Pins::tftCs, HIGH);
  touchSpi.end();
  touchSpi.begin(Pins::sdSck, Pins::sdMiso, Pins::sdMosi, Pins::sdCs);
  sdOk = SD.begin(Pins::sdCs, touchSpi, 4000000);
  if (sdOk) SD.mkdir("/diario");
  return sdOk;
}

void diaryUnmount() {
  SD.end();
  restoreTouchSpi();
}

void diaryLog(const char* kind, const String& detail) {
  String line = nowClock() + " | ";
  line += kind;
  line += " | ";
  line += detail;
  line.replace('\n', ' ');
  if (line.length() > 180) line = line.substring(0, 180);
  if (diaryN < 10) diaryLines[diaryN++] = line;
  else {
    for (int i = 0; i < 9; i++) diaryLines[i] = diaryLines[i + 1];
    diaryLines[9] = line;
  }
  Serial.println(line);
  if (diaryPendN < 6) diaryPend[diaryPendN++] = line;

  bool trySd = (sdOk || millis() >= sdRetryAt) &&
               screen != Screen::Calibrate && prefs.isKey("tl3");
  if (!trySd) return;
  if (diaryMount()) {
    String path = "/diario/" + clockDate + ".txt";
    File f = SD.open(path.c_str(), FILE_APPEND);
    if (f) {
      f.println(line);
      f.close();
      diaryDayLines++;
    }
    diaryUnmount();
    sdRetryAt = 0;
  } else {
    diaryUnmount();
    sdRetryAt = millis() + 300000UL;
  }
}

void diaryFlushNet() {
  if (!diaryPendN || WiFi.status() != WL_CONNECTED) return;
  if (millis() - lastDiaryNet < 1500) return;
  lastDiaryNet = millis();
  String line = diaryPend[0];
  for (int i = 0; i < diaryPendN - 1; i++) diaryPend[i] = diaryPend[i + 1];
  diaryPendN--;
  String p = "{\"day\":\"";
  p += clockDate;
  p += "\",\"line\":\"";
  jsonEsc(line, p);
  p += "\"}";
  if (viaHop == 1) postJson(LAN_DIA, p, false);
  else if (viaHop == 2) postJson(TS_DIA, p, true);
}

void drawAsk();
void drawAskType();

void sendAsk(const String& agent, const String& q) {
  askAg = agent;
  askQ = q;
  askA = "consultando CONTROL...";
  askPending = true;
  String p = "{\"agent\":\"";
  jsonEsc(agent, p);
  p += "\",\"q\":\"";
  jsonEsc(q, p);
  p += "\",\"target\":\"";
  p += (agent == "Gemma" ? "gemma" : "chief");
  p += "\"}";
  postHop(p, LAN_ASK, TS_ASK, CLOUD_ASK);
  diaryLog("ASK", agent + " " + q);
}

const char* chipLab(int idx, int slot) {
  static const char* def[3] = {"MESA", "FOCO", "HOJE"};
  if (slot < 0 || slot > 2) return def[0];
  String sh = agShort[idx];
  sh.toUpperCase();
  if (sh == "CTL") { static const char* a[3] = {"AGORA", "FROTA", "HOJE"}; return a[slot]; }
  if (sh == "ORQ") { static const char* a[3] = {"PRATO", "BLOQUEIO", "PROXIMO"}; return a[slot]; }
  if (sh == "SRV") { static const char* a[3] = {"CAIU", "HOSTS", "JOBS"}; return a[slot]; }
  if (sh == "AGD") { static const char* a[3] = {"HOJE", "PROXIMO", "RSVP"}; return a[slot]; }
  if (sh == "VAL") { static const char* a[3] = {"AGENDA", "TEAMS", "ENVIO"}; return a[slot]; }
  if (sh == "ALL") { static const char* a[3] = {"AGENDA", "NF", "ENVIO"}; return a[slot]; }
  if (sh == "GRN") { static const char* a[3] = {"TESOURO", "PAGAR", "FOCO"}; return a[slot]; }
  if (sh == "CUR") { static const char* a[3] = {"VAGAS", "STATUS", "PROX"}; return a[slot]; }
  if (sh == "PLD") { static const char* a[3] = {"REUNIAO", "BLOQUEIO", "NOTA"}; return a[slot]; }
  if (sh == "HKG") { static const char* a[3] = {"HATKG", "RAG", "SESSAO"}; return a[slot]; }
  if (sh == "GMA") { static const char* a[3] = {"RESUMO", "MUDOU", "FROTA"}; return a[slot]; }
  if (sh == "CON") { static const char* a[3] = {"CONSELHO", "LEI", "FOCO"}; return a[slot]; }
  if (sh == "X") { static const char* a[3] = {"DRAFT", "POST", "FILA"}; return a[slot]; }
  if (sh == "HYG") { static const char* a[3] = {"VIDEO", "BRIEF", "FILA"}; return a[slot]; }
  if (sh == "TRN") { static const char* a[3] = {"ESTUDO", "CURSO", "FILA"}; return a[slot]; }
  if (sh == "DSK") { static const char* a[3] = {"RESUMO", "TEXTO", "FOCO"}; return a[slot]; }
  if (sh == "JEV") { static const char* a[3] = {"TRIAGE", "INBOX", "AUTO"}; return a[slot]; }
  if (sh == "WA") { static const char* a[3] = {"WHATS", "FILA", "HOJE"}; return a[slot]; }
  if (sh == "DIA") { static const char* a[3] = {"HOJE", "FECHAR", "FOCO"}; return a[slot]; }
  if (sh == "SLK") { static const char* a[3] = {"SLACK", "FILA", "HOJE"}; return a[slot]; }
  if (sh == "RAG") { static const char* a[3] = {"RAG", "HATKG", "SESSAO"}; return a[slot]; }
  return def[slot];
}

String chipQuery(int idx, int slot) {
  String name = agName[idx];
  String lab = chipLab(idx, slot);
  return "consulta " + name + ": " + lab;
}

String localAnswer(int idx, int slot) {
  String sh = agShort[idx];
  sh.toUpperCase();
  String lab = chipLab(idx, slot);
  if (lab == "AGORA" || lab == "MESA") {
    if (nowK) return kindLabel(nowK) + String(" · ") + nowAg + " · " + nowTitle;
    return brief.length() ? brief : "Fila limpa.";
  }
  if (lab == "FROTA") return String(working) + " ao vivo · " + String(agentsN) + " agentes · " + String(down) + " down";
  if (lab == "HOJE" || lab == "AGENDA") return hoje.length() ? hoje : "sem agenda hoje";
  if (lab == "PROXIMO" || lab == "PROX") return nextEvent.length() ? nextEvent : futuro;
  if (lab == "PRATO" || lab == "FOCO") return mit.length() ? mit : (foco.length() ? foco : brief);
  if (lab == "BLOQUEIO") return String(kpi[7]) + " ciclos bloqueados · " + String(alerts) + " na fila";
  if (lab == "CAIU") return down ? (String(down) + " hosts down") : "todos os hosts up";
  if (lab == "HOSTS") return String(kpi[4]) + " up / " + String(kpi[5]) + " down";
  if (lab == "JOBS" || lab == "VAGAS") return String(kpi[6]) + " candidaturas";
  if (lab == "RSVP") return String(alerts) + " pedindo voce na fila";
  if (lab == "CONSELHO" || lab == "LEI") return consel.length() ? consel : "sem conselho fresco";
  if (lab == "TESOURO" || lab == "PAGAR") return agHead[idx].length() ? agHead[idx] : "Grana sem headline";
  if (lab == "REUNIAO" || lab == "NOTA" || lab == "SESSAO") return agHead[idx].length() ? agHead[idx] : "nada na mesa";
  if (lab == "HATKG" || lab == "RAG") return agHead[idx].length() ? agHead[idx] : "HatKG sem item na mesa";
  if (lab == "RESUMO" || lab == "MUDOU") return brief + " · " + (mit.length() ? mit : foco);
  if (lab == "STATUS" || lab == "ESTUDO" || lab == "CURSO" || lab == "VIDEO" || lab == "BRIEF" || lab == "DRAFT" || lab == "POST")
    return agHead[idx].length() ? agHead[idx] : (agAct[idx].length() ? agAct[idx] : "nada na mesa");
  if (lab == "FILA" || lab == "NF" || lab == "TEAMS" || lab == "ENVIO" || lab == "WHATS" || lab == "INBOX" || lab == "TRIAGE" || lab == "AUTO") {
    if (agLoad[idx] > 0) return String(agLoad[idx]) + " na mesa · " + agHead[idx];
    return "mesa vazia neste agente";
  }
  if (lab == "FECHAR" || lab == "TEXTO") return agHead[idx].length() ? agHead[idx] : (consel.length() ? consel : brief);
  if (ancora.length()) return ancora;
  return agHead[idx].length() ? agHead[idx] : brief;
}

void openAsk(int idx, int slot) {
  askAg = agName[idx];
  askQ = chipQuery(idx, slot);
  askA = localAnswer(idx, slot);
  sendAsk(askAg, askQ);
  drawAsk();
}

void loadTagged(const char* prefix, char src, int maxn) {
  listCount = 0;
  for (int i = 1; i <= maxn && listCount < 8; i++) {
    String row = field(ctrlBody, String(prefix) + String(i));
    if (!row.length()) break;
    String id = pipe(row, 3);
    if (skipped(id)) continue;
    listA[listCount] = pipe(row, 1).length() ? pipe(row, 1) : pipe(row, 0);
    listB[listCount] = pipe(row, 2);
    listC[listCount] = pipe(row, 0);
    listId[listCount] = id;
    listK[listCount] = kindOf(listA[listCount], id, src);
    listCount++;
  }
  cursor = 0;
  listScroll = 0;
}

void loadFila() {
  listCount = 0;
  const char* prefs[] = {"IN", "TK", "SV"};
  char srcs[] = {'M', 'T', 'S'};
  int maxn[] = {8, 8, 6};
  for (int p = 0; p < 3 && listCount < 8; p++) {
    for (int i = 1; i <= maxn[p] && listCount < 8; i++) {
      String row = field(ctrlBody, String(prefs[p]) + String(i));
      if (!row.length()) break;
      String id = pipe(row, 3);
      if (skipped(id)) continue;
      listA[listCount] = pipe(row, 1);
      listB[listCount] = pipe(row, 2);
      listC[listCount] = pipe(row, 0);
      listId[listCount] = id;
      listK[listCount] = kindOf(listA[listCount], id, srcs[p]);
      listCount++;
    }
  }
  cursor = 0;
  listScroll = 0;
}

void loadAgentItems() {
  listCount = 0;
  const char* prefs[] = {"IN", "TK", "EV", "SV"};
  char srcs[] = {'M', 'T', 'E', 'S'};
  int maxn[] = {8, 8, 6, 6};
  String want = agName[agCursor];
  for (int p = 0; p < 4 && listCount < 8; p++) {
    for (int i = 1; i <= maxn[p] && listCount < 8; i++) {
      String row = field(ctrlBody, String(prefs[p]) + String(i));
      if (!row.length()) break;
      if (pipe(row, 0) != want) continue;
      String id = pipe(row, 3);
      if (skipped(id)) continue;
      listA[listCount] = pipe(row, 1);
      listB[listCount] = pipe(row, 2);
      listC[listCount] = want;
      listId[listCount] = id;
      listK[listCount] = kindOf(listA[listCount], id, srcs[p]);
      listCount++;
    }
  }
  cursor = 0;
  listScroll = 0;
}

void removeCursor() {
  if (cursor < 0 || cursor >= listCount) return;
  skip(listId[cursor]);
  for (int i = cursor; i < listCount - 1; i++) {
    listA[i] = listA[i + 1]; listB[i] = listB[i + 1];
    listC[i] = listC[i + 1]; listId[i] = listId[i + 1]; listK[i] = listK[i + 1];
  }
  listCount--;
  if (cursor >= listCount) cursor = listCount - 1;
  if (cursor < 0) cursor = 0;
  pickNow();
}

int maxScroll() { return max(0, listCount * kRow - kListH); }
bool isListScreen() { return screen == Screen::Fila || screen == Screen::Agenda; }

void connectWifi() {
  if (!ssid.length()) { ssid = WIFI_SSID; pass = WIFI_PASS; }
  Serial.printf("WiFi begin %s\n", ssid.c_str());
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.disconnect(true, true);
  delay(120);
  WiFi.begin(ssid.c_str(), pass.c_str());
  connecting = true;
  connectStarted = millis();
}

int visCount() { return min(24, agTotal); }
int visIndex(int slot) { return slot; }
void cellXY(int slot, int& x, int& y) {
  x = 5 + (slot % 5) * 63;
  y = 36 + (slot / 5) * 32;
}

uint16_t agHue(int idx) {
  uint16_t tc = teamColor(agTeam[idx]);
  if (agShort[idx] == "WA") return YELLOW;
  return tc;
}

void drawGlyph(const String& sh, int cx, int cy, uint16_t fg) {
  if (sh == "CTL") { lcd.fillCircle(cx, cy, 3, YELLOW); return; }
  if (sh == "ORQ") {
    lcd.fillCircle(cx - 4, cy, 2, fg);
    lcd.fillCircle(cx, cy, 2, YELLOW);
    lcd.fillCircle(cx + 4, cy, 2, fg);
    return;
  }
  if (sh == "SRV") {
    lcd.drawFastHLine(cx - 5, cy - 4, 10, fg);
    lcd.drawFastHLine(cx - 5, cy, 10, fg);
    lcd.drawFastHLine(cx - 5, cy + 4, 10, fg);
    return;
  }
  if (sh == "AGD") { lcd.drawCircle(cx, cy, 5, fg); lcd.drawFastHLine(cx - 3, cy, 6, fg); return; }
  if (sh == "WA") { lcd.drawCircle(cx, cy - 1, 5, fg); lcd.drawPixel(cx - 4, cy + 5, fg); return; }
  if (sh == "X") { lcd.drawLine(cx - 4, cy - 4, cx + 4, cy + 4, fg); lcd.drawLine(cx + 4, cy - 4, cx - 4, cy + 4, fg); return; }
  if (sh == "HYG") { lcd.fillTriangle(cx - 4, cy - 4, cx - 4, cy + 4, cx + 5, cy, fg); return; }
  if (sh == "HKG" || sh == "RAG") { lcd.drawCircle(cx, cy, 4, fg); lcd.drawFastVLine(cx, cy - 4, 8, fg); return; }
  if (sh == "GRN") { lcd.drawCircle(cx, cy, 4, YELLOW); lcd.drawPixel(cx, cy, YELLOW); return; }
  if (sh == "DIA") { lcd.drawFastVLine(cx - 3, cy - 5, 10, fg); lcd.drawFastVLine(cx + 3, cy - 5, 10, fg); lcd.drawFastHLine(cx - 3, cy + 5, 6, fg); return; }
  if (sh == "SLK") { center("#", cx, cy - 3, 1, fg); return; }
  if (sh == "PLD") {
    lcd.drawFastVLine(cx - 3, cy - 3, 6, fg);
    lcd.drawFastVLine(cx, cy - 5, 10, fg);
    lcd.drawFastVLine(cx + 3, cy - 2, 4, fg);
    return;
  }
  String s = sh.substring(0, 1);
  center(s, cx, cy - 3, 1, fg);
}

void drawAvatar(int idx, int cx, int cy, int r) {
  bool run = agentBusy[idx];
  uint16_t ring = run ? YELLOW : MUTED;
  lcd.fillCircle(cx, cy, r, BG);
  lcd.drawCircle(cx, cy, r, ring);
  lcd.drawCircle(cx, cy, r - 1, ring);
  drawGlyph(agShort[idx], cx, cy, YELLOW);
}

void drawOneCell(int slot);

void agCenter(int idx, int& cx, int& cy) {
  int x, y;
  cellXY(idx, x, y);
  cx = x + 30;
  cy = y + 12;
}

void drawTicker() {
  lcd.fillRect(0, 194, 320, 8, BG);
  int n = visCount();
  int live = 0;
  for (int i = 0; i < n; i++) if (agentBusy[i] || agLoad[i] > 0) live++;
  uint16_t col = live ? YELLOW : MUTED;
  for (int p = 0; p < 6; p++) {
    int x = (crewPhase * 2 + p * 54) % 328 - 4;
    if (x > 1 && x < 318) lcd.fillCircle(x, 198, 2, col);
  }
}

void animFrotaLite() {
  crewPhase++;
  drawTicker();
  int n = visCount();
  for (int slot = 0; slot < n; slot++) {
    int x, y;
    cellXY(slot, x, y);
    int idx = visIndex(slot);
    int lx = x + 38, ly = y + 4;
    if (agentBusy[idx]) lcd.fillCircle(lx, ly, 2, (crewPhase & 1) ? YELLOW : PAPER);
    else lcd.fillCircle(lx, ly, 2, BG);
  }
}

void drawOneCell(int slot) {
  int idx = visIndex(slot);
  if (idx < 0 || idx >= agTotal) return;
  int x, y; cellXY(slot, x, y);
  int cx = x + 30, cy = y + 12;
  bool run = agentBusy[idx];
  drawAvatar(idx, cx, cy, 11);
  String sh = agShort[idx];
  if (sh.length() > 3) sh = sh.substring(0, 3);
  center(sh, cx, y + 24, 1, run ? YELLOW : PAPER);
  if (agLoad[idx] > 0) {
    lcd.fillCircle(cx + 8, cy - 8, 3, YELLOW);
  }
}

void labelsFor(char k, const char*& a, const char*& b, const char*& c, uint16_t& ca, uint16_t& cb, uint16_t& cc) {
  if (k == 'O') {
    a = "Enviar"; b = "Depois"; c = "Recusar";
    ca = YELLOW; cb = PANEL; cc = RED;
  } else if (k == 'R') {
    a = "Aceitar"; b = "Recap"; c = "Recusar";
    ca = YELLOW; cb = PANEL; cc = RED;
  } else if (k == 'T') {
    a = "Feito"; b = "Depois"; c = "Recusar";
    ca = YELLOW; cb = PANEL; cc = RED;
  } else if (k == 'S') {
    a = "Ciente"; b = "Depois"; c = "Recusar";
    ca = YELLOW; cb = PANEL; cc = RED;
  } else {
    a = "Aprovar"; b = "Depois"; c = "Recusar";
    ca = YELLOW; cb = PANEL; cc = RED;
  }
}

void drawActionRow(char k, int y) {
  const char *a, *b, *c; uint16_t ca, cb, cc;
  labelsFor(k, a, b, c, ca, cb, cc);
  button(8, y, 98, 36, a, ca, INK);
  button(112, y, 98, 36, b, PANEL, PAPER);
  button(216, y, 96, 36, c, RED, WHITE);
}

void fireBtn(const String& id, char k, int btn) {
  if (!id.length()) return;
  if (k == 'O') {
    if (btn == 0) sendKind(id, "approve", "\"payload\":{\"send\":true}");
    else if (btn == 1) sendKind(id, "defer");
    else sendKind(id, "reject");
  } else if (k == 'R') {
    if (btn == 0) sendKind(id, "rsvp", "\"payload\":{\"rsvp\":\"accept\"}");
    else if (btn == 1) sendKind(id, "rsvp", "\"payload\":{\"rsvp\":\"recap\"}");
    else sendKind(id, "rsvp", "\"payload\":{\"rsvp\":\"decline\"}");
  } else if (k == 'T') {
    if (btn == 0) sendKind(id, "task", "\"payload\":{\"status\":\"done\"}");
    else if (btn == 1) sendKind(id, "defer");
    else sendKind(id, "reject");
  } else {
    if (btn == 0) sendKind(id, "approve");
    else if (btn == 1) sendKind(id, "defer");
    else sendKind(id, "reject");
  }
}

void flashBtn(int x, int y, int w, int h, const char* msg) {
  center(msg, x + w / 2, y + (h - 8) / 2, 1, YELLOW);
  beep(1500, 40);
  delay(220);
}

void drawHome();
void drawFila();
void drawAgenda();
void drawFrota();
void drawNums();
void drawAgent();
void drawItem();
void drawAsk();
void drawAskType();
void drawSettings();
void drawDiary();
void drawListBody();

void kpiTile(int x, int y, int w, int h, const char* lab, int val, uint16_t accent) {
  lcd.setTextColor(accent); lcd.setTextSize(2);
  lcd.setCursor(x + 4, y + 4); lcd.print(val);
  lcd.setTextColor(MUTED); lcd.setTextSize(1);
  lcd.setCursor(x + 4, y + 24); lcd.print(lab);
}

void drawHome() {
  header("o que pede voce");
  uint16_t accent = nowK ? kindColor(nowK) : YELLOW;
  if (nowK) lcd.fillRect(8, 42, 3, 68, accent);
  if (nowK) {
    lcd.setTextColor(YELLOW); lcd.setTextSize(1); lcd.setCursor(20, 44);
    lcd.print(kindLabel(nowK));
    lcd.setTextColor(MUTED); lcd.print("  ");
    lcd.print(nowAg.substring(0, 16));
    wrap(nowTitle, 20, 62, 280, 14, PAPER, nowTitle.length() > 28 ? 1 : 2, 2);
    lcd.setTextColor(MUTED); lcd.setTextSize(1); lcd.setCursor(20, 96);
    lcd.print(nowWho.substring(0, 34));
  } else {
    wrap(foco.length() ? foco : "Fila limpa. Abra a frota ou fale com o assistente.", 20, 52, 280, 16, PAPER, 1, 3);
  }

  if (nowK) drawActionRow(nowK, 120);
  else {
    button(8, 120, 98, 36, "Fila", YELLOW);
    button(112, 120, 98, 36, "Frota", PANEL, PAPER);
    button(216, 120, 96, 36, "Guia", PANEL, PAPER);
  }

  kpiTile(8, 160, 100, 38, "fila", alerts, alerts ? YELLOW : MUTED);
  kpiTile(112, 160, 100, 38, "ao vivo", working, working ? YELLOW : MUTED);
  kpiTile(216, 160, 96, 38, "caiu", down, down ? RED : MUTED);

  drawNav(-1);
  screen = Screen::Home;
}

void drawListBody() {
  lcd.fillRect(0, kListTop, 320, kListH, BG);
  if (!listCount) return;
  for (int i = 0; i < listCount; i++) {
    int y = kListTop + i * kRow - listScroll;
    if (y + kRow < kListTop || y >= kListTop + kListH) continue;
    uint16_t kc = kindColor(listK[i]);
    lcd.fillCircle(14, y + 18, 3, kc);
    lcd.drawFastHLine(8, y + 39, 304, MUTED);
    lcd.setTextColor(kc); lcd.setTextSize(1);
    lcd.setCursor(18, y + 6); lcd.print(kindLabel(listK[i]));
    lcd.setTextColor(MUTED); lcd.print("  "); lcd.print(listC[i].substring(0, 16));
    lcd.setTextColor(WHITE); lcd.setCursor(18, y + 20);
    lcd.print(listA[i].substring(0, 36));
  }
}

void drawFila() {
  header("fila");
  if (!listCount) {
    wrap("Nada pedindo voce. A frota segue em espera.", 16, 80, 288, 18, PAPER, 1, 3);
  } else drawListBody();
  drawNav(0);
  screen = Screen::Fila;
  listScreen = Screen::Fila;
}

void drawAgenda() {
  header("hoje");
  if (!listCount) {
    wrap("Agenda vazia neste ciclo.", 16, 80, 288, 18, PAPER, 1, 3);
  } else drawListBody();
  lcd.setTextColor(MUTED); lcd.setTextSize(1); lcd.setCursor(12, 186);
  lcd.print((futuro.length() ? futuro : "").substring(0, 40));
  drawNav(1);
  screen = Screen::Agenda;
  listScreen = Screen::Agenda;
}

void drawFrota() {
  header("frota");
  lcd.fillRect(0, 34, 320, 160, BG);
  int n = visCount();
  if (n <= 0) wrap("Aguardando agentes do CONTROL...", 16, 90, 288, 16, MUTED, 1, 2);
  else for (int slot = 0; slot < n; slot++) drawOneCell(slot);
  drawTicker();
  drawNav(2);
  screen = Screen::Frota;
}

void drawItem() {
  char k = (cursor >= 0 && cursor < listCount) ? listK[cursor] : 'M';
  header(kindLabel(k));
  lcd.fillRect(8, 44, 3, 78, kindColor(k));
  lcd.setTextColor(MUTED); lcd.setTextSize(1); lcd.setCursor(20, 48);
  lcd.print(listC[cursor]);
  wrap(listA[cursor], 20, 64, 280, 16, WHITE, 1, 3);
  lcd.setTextColor(MUTED); lcd.setCursor(20, 108);
  lcd.print(listB[cursor].substring(0, 40));
  drawActionRow(k, 136);
  button(8, 184, 304, 16, "voltar", PANEL, MUTED);
  screen = Screen::Item;
}

void drawAgent() {
  header("agente");
  bool run = agentBusy[agCursor];
  uint16_t tc = teamColor(agTeam[agCursor]);
  if (agShort[agCursor] == "WA") tc = YELLOW;
  drawAvatar(agCursor, 28, 58, 14);
  lcd.setTextColor(WHITE); lcd.setTextSize(2); lcd.setCursor(48, 44);
  lcd.print(agName[agCursor].substring(0, 12));
  lcd.setTextSize(1); lcd.setTextColor(tc); lcd.setCursor(44, 68);
  lcd.print(agTeam[agCursor]);
  lcd.setTextColor(run ? YELLOW : MUTED);
  lcd.print(run ? "  ao vivo" : "  espera");
  if (agLoad[agCursor] > 0) {
    lcd.setTextColor(YELLOW);
    lcd.print("  ");
    lcd.print(agLoad[agCursor]);
    lcd.print(" mesa");
  }
  wrap(agHead[agCursor].length() ? agHead[agCursor] : agRole[agCursor], 12, 94, 296, 12, PAPER, 1, 1);

  lcd.setTextColor(MUTED); lcd.setTextSize(1); lcd.setCursor(12, 110);
  lcd.print("consulta guiada");
  for (int s = 0; s < 3; s++) {
    button(8 + s * 104, 122, 100, 26, chipLab(agCursor, s), PANEL, YELLOW);
  }

  int show = min(2, listCount);
  if (!show) {
    wrap(agAct[agCursor].length() ? agAct[agCursor] : "Nada na mesa. Toque uma consulta ou pergunte.", 16, 160, 288, 14, MUTED, 1, 2);
  } else {
    for (int i = 0; i < show; i++) {
      int y = 152 + i * 24;
      lcd.fillCircle(14, y + 10, 3, kindColor(listK[i]));
      lcd.setTextColor(kindColor(listK[i])); lcd.setTextSize(1); lcd.setCursor(16, y + 7);
      lcd.print(kindLabel(listK[i]));
      lcd.setTextColor(WHITE); lcd.print(" "); lcd.print(listA[i].substring(0, 24));
    }
  }
  button(8, 204, 150, 28, "VOLTAR", PANEL, PAPER);
  button(166, 204, 146, 28, "PERGUNTAR", YELLOW);
  screen = Screen::Agent;
}

void drawAsk() {
  header("consulta");
  lcd.setTextColor(YELLOW); lcd.setTextSize(1); lcd.setCursor(12, 42);
  lcd.print(askAg.substring(0, 14));
  lcd.setTextColor(MUTED); lcd.print("  ·  ");
  lcd.print(askPending ? "ao vivo" : "local+CONTROL");
  wrap(askQ, 14, 56, 292, 12, MUTED, 1, 1);
  lcd.fillRect(8, 88, 3, 108, YELLOW);
  wrap(askA.length() ? askA : "...", 18, 98, 284, 14, WHITE, 1, 6);
  button(8, 204, 150, 28, "VOLTAR", PANEL, PAPER);
  button(166, 204, 146, 28, "DE NOVO", YELLOW, INK);
  screen = Screen::Ask;
}

void drawAskType() {
  header("perguntar");
  lcd.setTextColor(MUTED); lcd.setTextSize(1); lcd.setCursor(12, 40);
  lcd.print(askAg.substring(0, 16));
  lcd.drawFastHLine(10, 80, 300, MUTED);
  lcd.setTextColor(WHITE); lcd.setTextSize(1); lcd.setCursor(16, 64);
  String shown = typedAsk;
  if (shown.length() > 38) shown = shown.substring(shown.length() - 38);
  lcd.print(shown.length() ? shown : "escreva a consulta...");
  const char* keys = keyboardUpper ? kKeysUpper : kKeysLower;
  for (int i = 0; i < 40; i++) {
    int col = i % 10, row = i / 10;
    button(4 + col * 31, 88 + row * 26, 29, 22, String(keys[i]), keys[i] == '<' ? RED : PANEL, WHITE);
  }
  button(4, 198, 70, 34, keyboardUpper ? "abc" : "ABC", PANEL, PAPER);
  button(78, 198, 70, 34, "ESPACO", PANEL, PAPER);
  button(152, 198, 70, 34, "VOLTAR", PANEL, PAPER);
  button(226, 198, 90, 34, "ENVIAR", YELLOW);
  screen = Screen::AskType;
}

void openAgent(int idx) {
  if (idx < 0 || idx >= agTotal) return;
  agCursor = idx;
  fromAgent = true;
  loadAgentItems();
  drawAgent();
}

void openFila() { fromAgent = false; loadFila(); drawFila(); }
void openAgenda() { fromAgent = false; loadTagged("EV", 'E', 6); drawAgenda(); }
void openFrota() { drawFrota(); }
void openNums() { drawNums(); }

void openTalk() {
  fromTalk = true;
  fromAgent = false;
  askAg = "orquestrador";
  if (!askA.length()) {
    askQ = "oi";
    askA = "Oi. Posso falar do seu dia: recados, tarefas, reunioes e o que ficou pendente.";
  }
  drawTalk();
}

void drawTalk() {
  header("guia");
  lcd.setTextColor(MUTED); lcd.setTextSize(1); lcd.setCursor(12, 38);
  lcd.print("conectar o audio em");
  button(8, 52, 150, 32, "computador", vozPlaca ? PANEL : YELLOW, vozPlaca ? PAPER : INK);
  button(166, 52, 146, 32, "fone", vozPlaca ? YELLOW : PANEL, vozPlaca ? INK : PAPER);
  lcd.setTextColor(YELLOW); lcd.setCursor(12, 90);
  if (vozPlaca) lcd.print(btLinked ? btPeer : "toque fone e pareie o Soundcore");
  else lcd.print("Soundcore neste PC");
  lcd.setTextColor(MUTED); lcd.setCursor(12, 104);
  lcd.print(askQ.length() ? askQ.substring(0, 38) : "pergunte a parede");
  wrap(askA.length() ? askA : "Pergunte do seu dia. Recados, tarefas, reunioes, pendencias.", 12, 118, 296, 14, PAPER, 1, 3);
  button(8, 168, 150, 28, "Ouvir", YELLOW);
  button(166, 168, 146, 28, "Escrever", PANEL, PAPER);
  drawNav(4);
  screen = Screen::Talk;
}

void drawNums() {
  header(numPage ? "reunioes por dia" : "indicadores");
  if (numPage == 0) {
    kpiTile(8, 40, 100, 44, "PROJETOS", kpi[0], YELLOW);
    kpiTile(112, 40, 100, 44, "HOJE", kpi[1], YELLOW);
    kpiTile(216, 40, 96, 44, "FEITO", kpi[2], PAPER);
    kpiTile(8, 88, 100, 44, "FILA", kpi[3], AMBER);
    kpiTile(112, 88, 100, 44, "HOSTS UP", kpi[4], YELLOW);
    kpiTile(216, 88, 96, 44, "CAIU", kpi[5], RED);
    lcd.setTextColor(MUTED); lcd.setTextSize(1); lcd.setCursor(12, 136);
    lcd.print("empresa  proj  reun  abertas  feitas");
    int maxv = 1;
    for (int i = 0; i < coCount; i++) {
      int s = coProj[i] + coMeet[i] + coOpen[i] + coDone[i];
      if (s > maxv) maxv = s;
    }
    int rows = min(coCount, 3);
    for (int i = 0; i < rows; i++) {
      int y = 148 + i * 16;
      lcd.setTextColor(WHITE); lcd.setCursor(12, y);
      String nm = coName[i];
      if (nm.length() > 8) nm = nm.substring(0, 8);
      lcd.print(nm);
      lcd.setTextColor(YELLOW); lcd.setCursor(78, y); lcd.print(coProj[i]);
      lcd.setTextColor(YELLOW); lcd.setCursor(128, y); lcd.print(coMeet[i]);
      lcd.setTextColor(AMBER); lcd.setCursor(178, y); lcd.print(coOpen[i]);
      lcd.setTextColor(PAPER); lcd.setCursor(240, y); lcd.print(coDone[i]);
    }
  } else {
    lcd.setTextColor(MUTED); lcd.setTextSize(1); lcd.setCursor(12, 44);
    lcd.print("dia        reunioes     feitas");
    int maxn = 1;
    for (int i = 0; i < dyCount; i++) if (dyMeet[i] > maxn) maxn = dyMeet[i];
    for (int i = 0; i < dyCount && i < 5; i++) {
      int y = 62 + i * 26;
      lcd.setTextColor(YELLOW); lcd.setCursor(16, y + 7); lcd.print(dyLab[i]);
      int bar = constrain(200 * dyMeet[i] / maxn, 4, 200);
      lcd.drawFastHLine(88, y + 11, bar, YELLOW);
      lcd.setTextColor(WHITE); lcd.setCursor(292 - textW(String(dyMeet[i]) + " / " + String(dyDone[i])), y + 7);
      lcd.print(String(dyMeet[i]) + "/" + String(dyDone[i]));
    }
    if (!dyCount) wrap("Sem reunioes classificadas.", 16, 80, 288, 16, MUTED, 1, 2);
  }
  drawNav(3);
  screen = Screen::Nums;
}

void redrawCurrentList() {
  if (listScreen == Screen::Agenda) drawAgenda();
  else drawFila();
}

void drawSettings() {
  header("ajustes");
  cardBox(8, 40, 304, 80, WiFi.status() == WL_CONNECTED ? YELLOW : AMBER);
  lcd.setTextColor(WHITE); lcd.setTextSize(2); lcd.setCursor(20, 50);
  lcd.print(WiFi.status() == WL_CONNECTED ? "WI-FI ON" : "WI-FI OFF");
  lcd.setTextSize(1); lcd.setTextColor(MUTED); lcd.setCursor(20, 74);
  lcd.print(ssid.length() ? ssid : WIFI_SSID);
  lcd.setCursor(20, 90);
  lcd.print(WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString() : "conectando...");
  const char* viaLab = viaHop == 1 ? "LAN" : viaHop == 2 ? "TS" : "NET";
  lcd.setTextColor(YELLOW); lcd.setCursor(180, 90); lcd.print(viaLab);
  lcd.setTextColor(sdOk ? YELLOW : AMBER); lcd.setCursor(20, 106);
  if (sdOk) { lcd.print("SD ok  "); lcd.print(diaryDayLines); lcd.print(" linhas hoje"); }
  else lcd.print("SD ausente — diario so na RAM");
  lcd.setTextColor(MUTED); lcd.setCursor(20, 118);
  lcd.print(vozPlaca ? (btLinked ? btPeer : "fone na placa — pareie CONTROL") : "fone neste PC");
  button(10, 132, 145, 28, "Fone PC", vozPlaca ? PANEL : YELLOW, vozPlaca ? PAPER : INK);
  button(165, 132, 145, 28, "Fone placa", vozPlaca ? YELLOW : PANEL, vozPlaca ? INK : PAPER);
  button(10, 166, 145, 28, "Calibrar", PANEL, PAPER);
  button(165, 166, 145, 28, "Diario", YELLOW);
  button(10, 204, 300, 28, "voltar", PANEL, MUTED);
  screen = Screen::Settings;
}

void drawDiary() {
  header("diario");
  tag(12, 40, 88, 14, sdOk ? "cartao SD" : "sem cartao", sdOk ? YELLOW : AMBER, INK);
  lcd.setTextColor(MUTED); lcd.setCursor(108, 43); lcd.print(clockDate);
  if (!diaryN) wrap("Ainda vazio. Acoes, consultas e boot entram aqui.", 12, 70, 296, 16, PAPER, 1, 3);
  else {
    int start = max(0, diaryN - 7);
    int row = 0;
    for (int i = start; i < diaryN; i++) {
      int y = 58 + row * 20;
      lcd.setTextColor(WHITE); lcd.setCursor(16, y + 5);
      lcd.print(diaryLines[i].substring(0, 37));
      row++;
    }
  }
  button(8, 204, 150, 28, "VOLTAR", PANEL, PAPER);
  button(166, 204, 146, 28, sdOk ? "OK" : "TENTAR SD", sdOk ? PANEL : YELLOW, sdOk ? MUTED : INK);
  screen = Screen::Diary;
}

void drawNetworks() {
  header("redes wi-fi");
  if (networkCount <= 0) wrap("Nenhuma rede. Aproxime do roteador.", 12, 60, 296, 18, PAPER, 1, 3);
  else {
    int start = networkPage * 4;
    for (int row = 0; row < 4; row++) {
      int idx = start + row;
      if (idx >= networkCount) break;
      String name = WiFi.SSID(idx);
      if (name.length() > 24) name = name.substring(0, 24);
      button(10, 46 + row * 36, 300, 32, name, row == 0 ? YELLOW : PANEL, row == 0 ? INK : PAPER);
    }
  }
  button(10, 210, 90, 22, "VOLTAR", PANEL, PAPER);
  button(110, 210, 95, 22, "ATUALIZAR", PANEL, PAPER);
  button(215, 210, 95, 22, "PROXIMAS", PANEL, PAPER);
  screen = Screen::Networks;
}

void scanNetworks() {
  header("buscando...");
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(80);
  networkCount = WiFi.scanNetworks(false, true);
  networkPage = 0;
  drawNetworks();
}

void drawPassword() {
  header("senha wi-fi");
  lcd.setTextColor(MUTED); lcd.setTextSize(1); lcd.setCursor(12, 44);
  lcd.print(pendingSsid.substring(0, 28));
  lcd.drawFastHLine(10, 82, 300, MUTED);
  String hidden;
  for (size_t i = 0; i < typedPass.length(); i++) hidden += '*';
  lcd.setTextColor(WHITE); lcd.setTextSize(2); lcd.setCursor(16, 62);
  lcd.print(hidden.substring(max(0, (int)hidden.length() - 22)));
  const char* keys = keyboardUpper ? kKeysUpper : kKeysLower;
  for (int i = 0; i < 40; i++) {
    int col = i % 10, row = i / 10;
    button(4 + col * 31, 88 + row * 26, 29, 22, String(keys[i]), keys[i] == '<' ? RED : PANEL, WHITE);
  }
  button(4, 198, 70, 34, keyboardUpper ? "abc" : "ABC", PANEL, PAPER);
  button(78, 198, 70, 34, "ESPACO", PANEL, PAPER);
  button(152, 198, 70, 34, "VOLTAR", PANEL, PAPER);
  button(226, 198, 90, 34, "CONECTAR", YELLOW);
  screen = Screen::Password;
}

int medianN(int* v, int n) {
  for (int i = 1; i < n; i++) {
    int x = v[i], j = i;
    while (j > 0 && v[j - 1] > x) { v[j] = v[j - 1]; j--; }
    v[j] = x;
  }
  return v[n / 2];
}

void drawCalTarget() {
  int x = kCalX[calStep], y = kCalY[calStep];
  uint16_t col = calStep < 4 ? YELLOW : YELLOW;
  lcd.fillCircle(x, y, 22, PANEL);
  lcd.drawCircle(x, y, 20, col);
  lcd.drawCircle(x, y, 12, col);
  lcd.drawFastHLine(x - 30, y, 61, col);
  lcd.drawFastVLine(x, y - 30, 61, col);
  lcd.fillCircle(x, y, 3, WHITE);
}

void drawCalibration() {
  lcd.fillScreen(BG);
  center("CALIBRAR TOQUE", 160, 8, 2, WHITE);
  if (calStep < 4) center("Toque e segure a cruz", 160, 28, 1, MUTED);
  else center("Toque o CENTRO para confirmar", 160, 28, 1, YELLOW);
  drawCalTarget();
  center(String(calStep + 1) + " / 5  ·  pressione firme", 160, 216, 1, MUTED);
  calN = 0;
  screen = Screen::Calibrate;
}

void mapRaw(int rx, int ry, int& sx, int& sy) {
  int ax = touchSwap ? ry : rx;
  int ay = touchSwap ? rx : ry;
  sx = constrain(map(ax, touchL, touchR, kCalX[0], kCalX[1]), 0, 319);
  sy = constrain(map(ay, touchT, touchB, kCalY[0], kCalY[2]), 0, 239);
}

bool sampleRaw(int& ox, int& oy) {
  int xs[16], ys[16];
  int n = 0;
  for (int i = 0; i < 16 && n < 16; i++) {
    TS_Point p = touch.getPoint();
    if (p.z <= 0) break;
    if (i >= 1) { xs[n] = p.x; ys[n] = p.y; n++; }
    delay(3);
  }
  if (n < 5) return false;
  ox = medianN(xs, n);
  oy = medianN(ys, n);
  return true;
}

bool computeCal() {
  int dx = abs(calX[1] - calX[0]) + abs(calX[2] - calX[3]);
  int dy = abs(calY[3] - calY[0]) + abs(calY[2] - calY[1]);
  int dxY = abs(calY[1] - calY[0]) + abs(calY[2] - calY[3]);
  int dyX = abs(calX[3] - calX[0]) + abs(calX[2] - calX[1]);
  touchSwap = (dxY + dyX) > (dx + dy) ? 1 : 0;
  int left, right, top, bot;
  if (!touchSwap) {
    left = (calX[0] + calX[3]) / 2;
    right = (calX[1] + calX[2]) / 2;
    top = (calY[0] + calY[1]) / 2;
    bot = (calY[2] + calY[3]) / 2;
  } else {
    left = (calY[0] + calY[3]) / 2;
    right = (calY[1] + calY[2]) / 2;
    top = (calX[0] + calX[1]) / 2;
    bot = (calX[2] + calX[3]) / 2;
  }
  if (abs(right - left) < 500 || abs(bot - top) < 400) return false;
  touchL = left; touchR = right; touchT = top; touchB = bot;
  Serial.printf("cal L=%d R=%d T=%d B=%d swap=%d\n", touchL, touchR, touchT, touchB, touchSwap);
  return true;
}

void saveCal() {
  prefs.putInt("tl3", touchL); prefs.putInt("tr3", touchR);
  prefs.putInt("tt3", touchT); prefs.putInt("tb3", touchB);
  prefs.putInt("tswap", touchSwap);
}

void finishCalFail() {
  calStep = 0;
  center("falhou — tente de novo", 160, 112, 1, RED);
  beep(400, 80);
  delay(900);
  drawCalibration();
}

void redrawAfterFetch() {
  if (screen == Screen::Home) drawHome();
  else if (screen == Screen::Agent) { loadAgentItems(); drawAgent(); }
  else if (screen == Screen::Frota) drawFrota();
  else if (screen == Screen::Nums) drawNums();
  else if (screen == Screen::Fila) { loadFila(); drawFila(); }
  else if (screen == Screen::Agenda) { loadTagged("EV", 'E', 6); drawAgenda(); }
  else if (screen == Screen::Ask && !askPending) drawAsk();
  else if (screen == Screen::Ask && askPending) drawAsk();
  else if (screen == Screen::Talk) drawTalk();
}

void applyBtn(int btn) {
  if (screen == Screen::Home) {
    if (!nowK) return;
    fireBtn(nowId, nowK, btn);
    flashBtn(8 + btn * 104, 120, btn == 2 ? 96 : 98, 36, btn == 2 ? "recusado" : btn == 1 ? "depois" : "ok");
    skip(nowId);
    pickNow();
    drawHome();
    return;
  }
  if (screen != Screen::Item || cursor < 0 || cursor >= listCount) return;
  char k = listK[cursor];
  fireBtn(listId[cursor], k, btn);
  flashBtn(8 + btn * 104, 136, btn == 2 ? 96 : 98, 40, btn == 2 ? "recusado" : btn == 1 ? "depois" : "ok");
  removeCursor();
  if (listCount > 0) drawItem();
  else if (fromAgent) drawAgent();
  else if (listScreen == Screen::Agenda) drawAgenda();
  else if (listScreen == Screen::Fila) drawFila();
  else drawHome();
}

void setup() {
  Serial.begin(115200);
  pinMode(Pins::backlight, OUTPUT); digitalWrite(Pins::backlight, HIGH);
  pinMode(Pins::speaker, OUTPUT);
  prefs.begin("control", false);
  vozPlaca = prefs.getBool("vozPlaca", false);
  if (vozPlaca) audioBtStart();
  ssid = WIFI_SSID;
  pass = WIFI_PASS;
  prefs.putString("ssid", ssid);
  prefs.putString("pass", pass);
  ctrlBody = prefs.getString("ctrl", "");
  if (ctrlBody.startsWith("CTRL/1")) parseCtrl(ctrlBody);
  touchL = prefs.getInt("tl3", 300); touchR = prefs.getInt("tr3", 3900);
  touchT = prefs.getInt("tt3", 300); touchB = prefs.getInt("tb3", 3900);
  touchSwap = prefs.getInt("tswap", 0);
  tftSpi.begin(Pins::tftSclk, Pins::tftMiso, Pins::tftMosi, Pins::tftCs);
  touchSpi.begin(Pins::touchSclk, Pins::touchMiso, Pins::touchMosi, Pins::touchCs);
  lcd.begin(40000000); lcd.setRotation(1);
  touch.begin(touchSpi); touch.setRotation(1);
  touchSpi.begin(Pins::touchSclk, Pins::touchMiso, Pins::touchMosi, Pins::touchCs);
  pinMode(Pins::sdCs, OUTPUT); digitalWrite(Pins::sdCs, HIGH);
  connectWifi();
  Serial.println("BOOT CONTROL kiosk plate");
  if (!prefs.isKey("tl3")) { calStep = 0; waitRelease = false; drawCalibration(); }
  else {
    diaryLog("BOOT", "CONTROL kiosk plate");
    drawHome();
  }
  beep(880, 50);
  Serial.println("CONTROL kiosk plate");
}

void loop() {
  if (connecting && (WiFi.status() == WL_CONNECTED || millis() - connectStarted > 22000)) {
    connecting = false;
    Serial.printf("WiFi status=%d ip=%s\n", WiFi.status(), WiFi.localIP().toString().c_str());
    if (WiFi.status() == WL_CONNECTED) {
      diaryLog("WIFI", WiFi.localIP().toString());
      fetchCtrl();
    } else diaryLog("WIFI", "falhou");
    if (screen == Screen::Home) drawHome();
    else if (screen == Screen::Settings) drawSettings();
  }
  uint32_t pollMs = viaHop == 1 ? 5000UL : viaHop == 2 ? 8000UL : 25000UL;
  if (WiFi.status() == WL_CONNECTED && millis() - lastFetch > pollMs && !fetching &&
      screen != Screen::Item && screen != Screen::Password && screen != Screen::Calibrate &&
      screen != Screen::Networks && screen != Screen::AskType) {
    if (fetchCtrl()) redrawAfterFetch();
  }

  TS_Point rawP = touch.getPoint();
  bool pressed = touch.touched() || rawP.z > 120;
  if (!pressed && diaryPendN) diaryFlushNet();
  if (screen == Screen::Frota && !pressed && millis() - lastAnim > 160) {
    lastAnim = millis();
    animFrotaLite();
  }
  static int lastBtN = -1;
  if (screen == Screen::BtList && btCount != lastBtN) {
    lastBtN = btCount;
    drawBtList();
  }
  if (screen == Screen::Calibrate) {
    if (waitRelease) {
      if (!pressed) waitRelease = false;
      delay(12);
      return;
    }
    if (!pressed) {
      if (calN > 0) { calN = 0; drawCalTarget(); }
      delay(12);
      return;
    }
    if (calN < 20) {
      calXs[calN] = rawP.x;
      calYs[calN] = rawP.y;
      calN++;
    }
    int px = kCalX[calStep], py = kCalY[calStep];
    int ring = 8 + calN;
    lcd.drawCircle(px, py, ring > 22 ? 22 : ring, YELLOW);
    if (calN < 8) { delay(12); return; }
    int rx = medianN(calXs, calN);
    int ry = medianN(calYs, calN);
    calX[calStep] = rx;
    calY[calStep] = ry;
    calN = 0;
    waitRelease = true;
    beep(1400, 35);
    lcd.fillCircle(px, py, 10, YELLOW);
    Serial.printf("cal %d raw=%d,%d z=%d\n", calStep, rx, ry, rawP.z);
    delay(180);
    if (calStep < 3) {
      calStep++;
      drawCalibration();
    } else if (calStep == 3) {
      if (!computeCal()) { finishCalFail(); return; }
      calStep = 4;
      drawCalibration();
    } else {
      int sx, sy;
      mapRaw(rx, ry, sx, sy);
      int dx = sx - kCalX[4], dy = sy - kCalY[4];
      Serial.printf("cal center mapped %d,%d\n", sx, sy);
      if (dx * dx + dy * dy > 70 * 70) { finishCalFail(); return; }
      saveCal();
      diaryLog("CAL", "ok");
      lcd.fillCircle(kCalX[4], kCalY[4], 12, YELLOW);
      center("ok", 160, 100, 2, YELLOW);
      beep(1800, 50);
      delay(350);
      drawHome();
    }
    return;
  }

  if (!pressed) {
    if (touchHeld && !dragged) {
      touchHeld = false;
      tapX = tapDownX;
      tapY = tapDownY;
      beep();
      goto handle_tap;
    }
    touchHeld = false;
    dragged = false;
    delay(16);
    return;
  }

  {
    TS_Point p = touch.getPoint();
    int sx, sy;
    mapRaw(p.x, p.y, sx, sy);
    tapX = sx;
    tapY = sy;
    if (!touchHeld) {
      int xs[16], ys[16], n = 0;
      for (int i = 0; i < 18 && touch.touched() && n < 16; i++) {
        TS_Point q = touch.getPoint();
        int qx, qy;
        mapRaw(q.x, q.y, qx, qy);
        if (i >= 2) { xs[n] = qx; ys[n] = qy; n++; }
        delay(3);
      }
      if (n >= 4) { tapX = medianN(xs, n); tapY = medianN(ys, n); }
      tapDownX = tapX;
      tapDownY = tapY;
      touchHeld = true;
      dragged = false;
      dragY0 = tapDownY;
      scroll0 = listScroll;
    } else if (isListScreen() && tapY < 200) {
      int dy = dragY0 - tapY;
      if (abs(dy) > 8) dragged = true;
      if (dragged) {
        int next = constrain(scroll0 + dy, 0, maxScroll());
        if (next != listScroll) { listScroll = next; drawListBody(); }
      }
    }
    delay(16);
    return;
  }

handle_tap:
  int x = tapDownX, y = tapDownY;
  if (y < 34 && x < 42 && screen != Screen::Calibrate && screen != Screen::Password &&
      screen != Screen::Item && screen != Screen::Networks && screen != Screen::AskType) {
    drawSettings();
    return;
  }

  if (screen == Screen::Home) {
    if (tapNav(x, y)) return;
    else if (hit(x, y, 8, 160, 100, 38)) openFila();
    else if (hit(x, y, 112, 160, 100, 38)) openFrota();
    else if (hit(x, y, 216, 160, 96, 38)) openNums();
    else if (y >= 120 && y < 156) {
      if (nowK) {
        if (x < 110) applyBtn(0);
        else if (x < 214) applyBtn(1);
        else applyBtn(2);
      } else {
        if (x < 110) openFila();
        else if (x < 214) openFrota();
        else openTalk();
      }
    } else if (nowK && y >= 38 && y < 118) {
      listCount = 1; cursor = 0; fromAgent = false;
      listA[0] = nowTitle; listB[0] = nowWho; listC[0] = nowAg; listId[0] = nowId; listK[0] = nowK;
      listScreen = Screen::Fila;
      drawItem();
    }
  } else if (screen == Screen::Fila || screen == Screen::Agenda) {
    if (tapNav(x, y)) return;
    else if (y < 200 && listCount) {
      int idx = (y - kListTop + listScroll) / kRow;
      if (idx >= 0 && idx < listCount) { cursor = idx; fromAgent = false; drawItem(); }
    }
  } else if (screen == Screen::Frota) {
    if (tapNav(x, y)) return;
    else if (y >= 40 && y < 200) {
      int n = visCount();
      for (int slot = 0; slot < n; slot++) {
        int cx, cy; cellXY(slot, cx, cy);
        if (hit(x, y, cx, cy, 60, 30)) { openAgent(visIndex(slot)); break; }
      }
    }
  } else if (screen == Screen::Nums) {
    if (tapNav(x, y)) return;
    else if (y < 200) {
      numPage = numPage ? 0 : 1;
      drawNums();
    }
  } else if (screen == Screen::Talk) {
    if (tapNav(x, y)) return;
    else if (hit(x, y, 8, 52, 150, 32)) {
      vozPlaca = false;
      prefs.putBool("vozPlaca", false);
      drawTalk();
    } else if (hit(x, y, 166, 52, 146, 32)) openBtList();
    else if (hit(x, y, 8, 168, 150, 28)) listenVoice();
    else if (hit(x, y, 166, 168, 146, 28) || (y >= 100 && y < 165)) {
      typedAsk = "";
      keyboardUpper = true;
      askAg = "orquestrador";
      fromTalk = true;
      drawAskType();
    }
  } else if (screen == Screen::Agent) {
    if (hit(x, y, 8, 204, 150, 28)) openFrota();
    else if (hit(x, y, 166, 204, 146, 28)) {
      typedAsk = "";
      keyboardUpper = true;
      askAg = agName[agCursor];
      fromTalk = false;
      drawAskType();
    } else if (y >= 120 && y < 148) {
      int slot = x < 110 ? 0 : x < 214 ? 1 : 2;
      openAsk(agCursor, slot);
    } else if (y >= 152 && y < 200 && listCount) {
      int idx = (y - 152) / 24;
      if (idx >= 0 && idx < min(2, listCount)) { cursor = idx; drawItem(); }
    }
  } else if (screen == Screen::Ask) {
    if (hit(x, y, 8, 204, 150, 28)) {
      if (fromTalk) drawTalk();
      else if (fromAgent) drawAgent();
      else drawHome();
    } else if (hit(x, y, 166, 204, 146, 28)) {
      sendAsk(askAg, askQ);
      drawAsk();
    }
  } else if (screen == Screen::AskType) {
    const char* keys = keyboardUpper ? kKeysUpper : kKeysLower;
    for (int i = 0; i < 40; i++) {
      int col = i % 10, row = i / 10;
      if (hit(x, y, 4 + col * 31, 88 + row * 26, 29, 22)) {
        char key = keys[i];
        if (key == '<') { if (typedAsk.length()) typedAsk.remove(typedAsk.length() - 1); }
        else if (typedAsk.length() < 80) typedAsk += key;
        drawAskType();
        return;
      }
    }
    if (hit(x, y, 4, 198, 70, 34)) { keyboardUpper = !keyboardUpper; drawAskType(); }
    else if (hit(x, y, 78, 198, 70, 34)) { if (typedAsk.length() < 80) typedAsk += ' '; drawAskType(); }
    else if (hit(x, y, 152, 198, 70, 34)) {
      if (fromTalk) drawTalk();
      else drawAgent();
    } else if (hit(x, y, 226, 198, 90, 34) && typedAsk.length()) {
      askQ = typedAsk;
      askA = "consultando CONTROL...";
      sendAsk(askAg, typedAsk);
      if (fromTalk) drawTalk();
      else drawAsk();
    }
  } else if (screen == Screen::Item) {
    if (y >= 136 && y < 176) {
      if (x < 110) applyBtn(0);
      else if (x < 214) applyBtn(1);
      else applyBtn(2);
    } else if (y >= 180) {
      if (fromAgent) drawAgent();
      else if (listScreen == Screen::Agenda) drawAgenda();
      else if (listScreen == Screen::Fila) drawFila();
      else drawHome();
    }
  } else if (screen == Screen::Settings) {
    if (y >= 70 && y < 110) scanNetworks();
    else if (hit(x, y, 10, 132, 145, 28)) {
      vozPlaca = false;
      prefs.putBool("vozPlaca", false);
      drawSettings();
    } else if (hit(x, y, 165, 132, 145, 28)) openBtList();
    else if (hit(x, y, 10, 166, 145, 28)) { calStep = 0; calN = 0; waitRelease = false; drawCalibration(); }
    else if (hit(x, y, 165, 166, 145, 28)) drawDiary();
    else if (hit(x, y, 10, 204, 300, 28)) drawHome();
  } else if (screen == Screen::BtList) {
    if (hit(x, y, 10, 204, 90, 28)) {
      if (fromTalk) drawTalk();
      else drawSettings();
    }
    else if (hit(x, y, 110, 204, 95, 28)) { btScan(); drawBtList(); }
    else if (hit(x, y, 215, 204, 95, 28) && btCount > 4) {
      btPage = (btPage + 1) % ((btCount + 3) / 4);
      drawBtList();
    } else {
      int start = btPage * 4;
      for (int row = 0; row < 4; row++) {
        int idx = start + row;
        if (idx < btCount && hit(x, y, 10, 58 + row * 32, 300, 28)) {
          strncpy(btPeer, btDevs[idx].name, 23);
          esp_a2d_source_connect(btDevs[idx].addr);
          askA = String("ligando ") + btPeer;
          drawBtList();
          return;
        }
      }
    }
  } else if (screen == Screen::Diary) {
    if (hit(x, y, 8, 204, 150, 28)) drawSettings();
    else if (hit(x, y, 166, 204, 146, 28) && !sdOk) {
      sdRetryAt = 0;
      diaryLog("SD", "tentativa manual");
      drawDiary();
    }
  } else if (screen == Screen::Networks) {
    for (int row = 0; row < 4; row++) {
      int idx = networkPage * 4 + row;
      if (idx < networkCount && hit(x, y, 10, 46 + row * 36, 300, 32)) {
        pendingSsid = WiFi.SSID(idx);
        typedPass = pendingSsid == ssid ? pass : "";
        keyboardUpper = true;
        drawPassword();
        return;
      }
    }
    if (hit(x, y, 10, 210, 90, 22)) drawSettings();
    else if (hit(x, y, 110, 210, 95, 22)) scanNetworks();
    else if (hit(x, y, 215, 210, 95, 22) && networkCount > 4) {
      networkPage = (networkPage + 1) % ((networkCount + 3) / 4);
      drawNetworks();
    }
  } else if (screen == Screen::Password) {
    const char* keys = keyboardUpper ? kKeysUpper : kKeysLower;
    for (int i = 0; i < 40; i++) {
      int col = i % 10, row = i / 10;
      if (hit(x, y, 4 + col * 31, 88 + row * 26, 29, 22)) {
        char key = keys[i];
        if (key == '<') { if (typedPass.length()) typedPass.remove(typedPass.length() - 1); }
        else if (typedPass.length() < 63) typedPass += key;
        drawPassword();
        return;
      }
    }
    if (hit(x, y, 4, 198, 70, 34)) { keyboardUpper = !keyboardUpper; drawPassword(); }
    else if (hit(x, y, 78, 198, 70, 34)) { if (typedPass.length() < 63) typedPass += ' '; drawPassword(); }
    else if (hit(x, y, 152, 198, 70, 34)) drawNetworks();
    else if (hit(x, y, 226, 198, 90, 34)) {
      ssid = pendingSsid;
      pass = typedPass;
      prefs.putString("ssid", ssid);
      prefs.putString("pass", pass);
      connectWifi();
      drawSettings();
    }
  }
}
