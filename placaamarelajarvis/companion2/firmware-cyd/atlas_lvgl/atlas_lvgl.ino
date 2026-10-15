#include <Arduino.h>
#include <SPI.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ILI9341.h>
#include <nvs.h>
#include <lvgl.h>

namespace Pins {
constexpr int tftSclk = 14, tftMosi = 13, tftMiso = 12, tftDc = 2, tftCs = 15, backlight = 21;
constexpr int touchSclk = 25, touchMosi = 32, touchMiso = 39, touchCs = 33, speaker = 26;
}

SPIClass tftSpi(VSPI);
Adafruit_ILI9341 tft(&tftSpi, Pins::tftDc, Pins::tftCs, -1);
static int touchL = 186, touchR = 3742, touchT = 229, touchB = 3940, touchSwap = 0;
static int outL = 0, outR = 319, outT = 0, outB = 239;

constexpr const char* LAN_CTRL = "http://192.168.15.4:8788/cyd";
constexpr const char* LAN_ACT = "http://192.168.15.4:8788/cyd/act";
constexpr const char* LAN_ASK = "http://192.168.15.4:8788/cyd/ask";
constexpr const char* LAN_LIS = "http://192.168.15.4:8788/cyd/listen";
constexpr const char* TS_CTRL = "https://cpqd8nr2jg4.taile5dcde.ts.net/cyd";
constexpr const char* TS_ACT = "https://cpqd8nr2jg4.taile5dcde.ts.net/cyd/act";
constexpr const char* TS_ASK = "https://cpqd8nr2jg4.taile5dcde.ts.net/cyd/ask";
constexpr const char* TS_LIS = "https://cpqd8nr2jg4.taile5dcde.ts.net/cyd/listen";
constexpr const char* CLOUD_CTRL = "https://control.ch8ai.com.br/cyd";
constexpr const char* CLOUD_ACT = "https://control.ch8ai.com.br/cyd/act";
constexpr const char* CLOUD_ASK = "https://control.ch8ai.com.br/cyd/ask";
constexpr const char* CLOUD_LIS = "https://control.ch8ai.com.br/cyd/listen";
constexpr const char* WIFI_SSID = "";
constexpr const char* WIFI_PASS = "";

static const uint16_t screenW = 320;
static const uint16_t screenH = 240;
static lv_disp_draw_buf_t drawBuf;
static lv_color_t buf1[screenW * 16];

static const uint32_t COL_BG = 0x16110C;
static const uint32_t COL_BAR = 0x100C08;
static const uint32_t COL_TILE = 0x241C14;
static const uint32_t COL_TILE2 = 0x2E2214;
static const uint32_t COL_GOLD = 0xE8B400;
static const uint32_t COL_PAPER = 0xE6DCC8;
static const uint32_t COL_MUTED = 0xB4A490;
static const uint32_t COL_INK = 0x100C08;

String ctrlBody, health = "OFF", brief, nextEvent, hoje, futuro, foco, mit, ancora, consel;
String nowTitle, nowWho, nowId, nowAg, skipIds, askA, askQ, askAg;
char nowK = 0;
int alerts = 0, tasksN = 0, agentsN = 0, working = 0, down = 0;
uint8_t viaHop = 0;
uint32_t skipLanUntil = 0, lastFetch = 0, connectStarted = 0;
bool connecting = false, fetching = false, askPending = false;
int kpi[8] = {};
String coName[6];
int coProj[6] = {}, coMeet[6] = {}, coOpen[6] = {}, coDone[6] = {}, coCount = 0;
String dyLab[5];
int dyMeet[5] = {}, dyDone[5] = {}, dyCount = 0;
String agName[24], agShort[24], agTeam[24], agAct[24], agHead[24], agRole[24];
bool agentBusy[24] = {};
int agLoad[24] = {};
int agTotal = 0, agCursor = 0, crewPhase = 0;
String clockDate = "--";
int clockSec = 0;
uint32_t clockBaseMs = 0;
String listA[8], listB[8], listId[8];
char listK[8] = {};
int listCount = 0;

lv_obj_t *uiBar, *uiHop, *uiClock, *uiGrid, *uiPage, *uiPageTitle, *uiPageBody;
lv_obj_t *tileVal[6];
lv_obj_t *uiActBar;
lv_obj_t *uiFrota, *uiFroStatus, *uiTickDot[6];
lv_obj_t *froCell[21], *froRing[21], *froName[21];
lv_obj_t *uiDia, *diaArc[3], *diaNum[3], *diaCap[3];
lv_obj_t *diaBar[5], *diaBarFill[5], *diaBarLab[5], *diaBarVal[5];
lv_obj_t *diaFoot;
lv_obj_t *uiGuia, *orbHalo, *orbMid, *orbCore, *orbHint, *orbSaid;
lv_obj_t *uiAgent, *agAvatar, *agNameL, *agMetaL, *agHeadL, *agNoteL;
lv_obj_t *agArc, *agArcN, *agBar[3], *agBarFill[3], *agBarLab[3], *agBarVal[3];
lv_obj_t *agScroll;
enum OrbMode { OrbIdle, OrbListen, OrbThink, OrbSpeak };
OrbMode orbMode = OrbIdle;
uint8_t orbPhase = 0;

enum Page { Home, Agora, Fila, Hoje, Frota, Guia, Dia, Agent };
Page page = Home;

void beep(int hz = 1400, int ms = 28) { tone(Pins::speaker, hz, ms); }

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

bool skipped(const String& id) {
  return id.length() && skipIds.indexOf("|" + id + "|") >= 0;
}

void skip(const String& id) {
  if (!id.length()) return;
  skipIds += "|" + id + "|";
  if (skipIds.length() > 400) skipIds = skipIds.substring(skipIds.length() - 200);
}

void pickNow() {
  nowK = 0;
  nowTitle = "";
  nowWho = "";
  nowId = "";
  nowAg = "";
  for (int i = 1; i <= 8 && !nowK; i++) {
    String row = field(ctrlBody, "IN" + String(i));
    if (!row.length()) break;
    String id = pipe(row, 3);
    if (skipped(id)) continue;
    nowAg = pipe(row, 0);
    nowTitle = pipe(row, 1);
    nowWho = pipe(row, 2);
    nowId = id;
    nowK = kindOf(nowTitle, nowId, 'M');
  }
  for (int i = 1; i <= 8 && !nowK; i++) {
    String row = field(ctrlBody, "TK" + String(i));
    if (!row.length()) break;
    String id = pipe(row, 3);
    if (skipped(id)) continue;
    nowAg = pipe(row, 0);
    nowTitle = pipe(row, 1);
    nowWho = pipe(row, 2);
    nowId = id;
    nowK = kindOf(nowTitle, nowId, 'T');
  }
}

void setClockFromStamp(const String& stamp) {
  if (stamp.length() < 19) return;
  clockDate = stamp.substring(0, 10);
  int h = stamp.substring(11, 13).toInt();
  int m = stamp.substring(14, 16).toInt();
  int s = stamp.substring(17, 19).toInt();
  bool utc = stamp.indexOf('Z') >= 0 || stamp.indexOf("+00") >= 0;
  if (utc) {
    h -= 3;
    if (h < 0) {
      h += 24;
    }
  }
  clockSec = h * 3600 + m * 60 + s;
  clockBaseMs = millis();
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
      askA = ans;
      askPending = false;
      if (page == Guia) orbMode = OrbSpeak;
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

void postHop(const String& payload, const char* lan, const char* ts, const char* cloud) {
  if (viaHop == 1) postJson(lan, payload, false);
  else if (viaHop == 2) postJson(ts, payload, true);
  else postJson(cloud, payload, true);
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
    if (ch == '\\' && i + 1 < raw.length()) {
      o += raw[++i];
      continue;
    }
    o += ch;
  }
  return o;
}

void jsonEsc(const String& s, String& out) {
  for (size_t i = 0; i < s.length(); i++) {
    char ch = s[i];
    if (ch == '"' || ch == '\\') out += '\\';
    if (ch >= 32) out += ch;
  }
}

void sendKind(const String& id, const char* kind, const char* extra = "") {
  if (!id.length()) return;
  String p = "{\"id\":\"";
  p += id;
  p += "\",\"kind\":\"";
  p += kind;
  p += "\"";
  if (extra && extra[0]) {
    p += ",";
    p += extra;
  }
  p += "}";
  postHop(p, LAN_ACT, TS_ACT, CLOUD_ACT);
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

void sendAsk(const String& agent, const String& q) {
  askAg = agent;
  askQ = q;
  askA = "Um instante, estou olhando o seu dia.";
  askPending = true;
  String p = "{\"agent\":\"";
  jsonEsc(agent, p);
  p += "\",\"q\":\"";
  jsonEsc(q, p);
  p += "\",\"target\":\"chief\"}";
  postHop(p, LAN_ASK, TS_ASK, CLOUD_ASK);
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
  parseCtrl(body);
  return true;
}

void connectWifi() {
  Serial.printf("WiFi begin %s\n", WIFI_SSID);
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.disconnect(true, true);
  delay(120);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  connecting = true;
  connectStarted = millis();
}

const char* chipLab(int idx, int slot) {
  static const char* def[3] = {"mesa", "foco", "hoje"};
  if (slot < 0 || slot > 2) return def[0];
  String sh = agShort[idx];
  sh.toUpperCase();
  if (sh == "CTL") { static const char* a[3] = {"agora", "frota", "hoje"}; return a[slot]; }
  if (sh == "ORQ") { static const char* a[3] = {"prato", "bloqueio", "proximo"}; return a[slot]; }
  if (sh == "SRV") { static const char* a[3] = {"caiu", "hosts", "jobs"}; return a[slot]; }
  if (sh == "AGD") { static const char* a[3] = {"hoje", "proximo", "rsvp"}; return a[slot]; }
  if (sh == "VAL") { static const char* a[3] = {"agenda", "teams", "envio"}; return a[slot]; }
  if (sh == "ALL") { static const char* a[3] = {"agenda", "nf", "envio"}; return a[slot]; }
  if (sh == "GRN") { static const char* a[3] = {"tesouro", "pagar", "foco"}; return a[slot]; }
  if (sh == "CUR") { static const char* a[3] = {"vagas", "status", "prox"}; return a[slot]; }
  if (sh == "PLD") { static const char* a[3] = {"reuniao", "bloqueio", "nota"}; return a[slot]; }
  if (sh == "HKG") { static const char* a[3] = {"hatkg", "rag", "sessao"}; return a[slot]; }
  if (sh == "GMA") { static const char* a[3] = {"resumo", "mudou", "frota"}; return a[slot]; }
  if (sh == "CON") { static const char* a[3] = {"conselho", "lei", "foco"}; return a[slot]; }
  if (sh == "X") { static const char* a[3] = {"draft", "post", "fila"}; return a[slot]; }
  if (sh == "HYG") { static const char* a[3] = {"video", "brief", "fila"}; return a[slot]; }
  if (sh == "TRN") { static const char* a[3] = {"estudo", "curso", "fila"}; return a[slot]; }
  if (sh == "DSK") { static const char* a[3] = {"resumo", "texto", "foco"}; return a[slot]; }
  if (sh == "JEV") { static const char* a[3] = {"triage", "inbox", "auto"}; return a[slot]; }
  if (sh == "WA") { static const char* a[3] = {"whats", "fila", "hoje"}; return a[slot]; }
  if (sh == "DIA") { static const char* a[3] = {"hoje", "fechar", "foco"}; return a[slot]; }
  if (sh == "SLK") { static const char* a[3] = {"slack", "fila", "hoje"}; return a[slot]; }
  if (sh == "RAG") { static const char* a[3] = {"rag", "hatkg", "sessao"}; return a[slot]; }
  return def[slot];
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
      listId[listCount] = id;
      listK[listCount] = kindOf(listA[listCount], id, srcs[p]);
      listCount++;
    }
  }
}

static void agent_cb(lv_event_t* e);
static void style_clear(lv_obj_t* o);

void ensureFrota() {
  if (froCell[0]) return;
  if (!uiFrota) return;
  uiFroStatus = lv_label_create(uiFrota);
  lv_label_set_text(uiFroStatus, "buscando a frota");
  lv_obj_set_style_text_color(uiFroStatus, lv_color_hex(COL_MUTED), 0);
  lv_obj_set_pos(uiFroStatus, 10, 0);

  for (int i = 0; i < 21; i++) {
    int col = i % 5;
    int row = i / 5;
    int x = 8 + col * 63;
    int y = 16 + row * 30;
    lv_obj_t* ring = lv_btn_create(uiFrota);
    froCell[i] = ring;
    froRing[i] = ring;
    lv_obj_set_size(ring, 24, 24);
    lv_obj_set_pos(ring, x + 16, y);
    style_clear(ring);
    lv_obj_set_style_radius(ring, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_bg_color(ring, lv_color_hex(COL_TILE), 0);
    lv_obj_set_style_bg_opa(ring, LV_OPA_COVER, 0);
    lv_obj_set_style_border_width(ring, 2, 0);
    lv_obj_set_style_border_color(ring, lv_color_hex(0x5A4A38), 0);
    lv_obj_clear_flag(ring, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_add_event_cb(ring, agent_cb, LV_EVENT_CLICKED, (void*)(intptr_t)i);
    lv_obj_add_flag(ring, LV_OBJ_FLAG_HIDDEN);
    lv_obj_t* g = lv_label_create(ring);
    lv_label_set_text(g, "·");
    lv_obj_set_style_text_color(g, lv_color_hex(COL_GOLD), 0);
    lv_obj_center(g);
    lv_obj_clear_flag(g, LV_OBJ_FLAG_CLICKABLE);

    lv_obj_t* nm = lv_label_create(uiFrota);
    froName[i] = nm;
    lv_label_set_text(nm, "");
    lv_obj_set_style_text_color(nm, lv_color_hex(COL_MUTED), 0);
    lv_obj_set_pos(nm, x + 14, y + 24);
    lv_obj_clear_flag(nm, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_add_flag(nm, LV_OBJ_FLAG_HIDDEN);
  }

  for (int p = 0; p < 6; p++) {
    uiTickDot[p] = lv_obj_create(uiFrota);
    lv_obj_set_size(uiTickDot[p], 5, 5);
    lv_obj_set_pos(uiTickDot[p], p * 54, 166);
    style_clear(uiTickDot[p]);
    lv_obj_set_style_radius(uiTickDot[p], LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_bg_color(uiTickDot[p], lv_color_hex(COL_GOLD), 0);
    lv_obj_set_style_bg_opa(uiTickDot[p], LV_OPA_COVER, 0);
    lv_obj_clear_flag(uiTickDot[p], LV_OBJ_FLAG_CLICKABLE);
  }
}

void refreshFrota() {
  ensureFrota();
  int live = 0;
  int n = agTotal;
  if (n > 21) n = 21;
  for (int i = 0; i < 21; i++) {
    if (!froCell[i]) continue;
    if (i >= n) {
      lv_obj_add_flag(froCell[i], LV_OBJ_FLAG_HIDDEN);
      if (froName[i]) lv_obj_add_flag(froName[i], LV_OBJ_FLAG_HIDDEN);
      continue;
    }
    lv_obj_clear_flag(froCell[i], LV_OBJ_FLAG_HIDDEN);
    if (froName[i]) lv_obj_clear_flag(froName[i], LV_OBJ_FLAG_HIDDEN);
    bool run = agentBusy[i];
    if (run) live++;
    lv_obj_set_style_border_color(froRing[i], lv_color_hex(run ? COL_GOLD : 0x5A4A38), 0);
    lv_obj_set_style_border_width(froRing[i], run ? 3 : 2, 0);
    String sh = agShort[i];
    if (sh.length() > 3) sh = sh.substring(0, 3);
    sh.toUpperCase();
    lv_label_set_text(froName[i], sh.c_str());
    lv_obj_set_style_text_color(froName[i], lv_color_hex(run ? COL_GOLD : COL_PAPER), 0);
    lv_obj_t* g = lv_obj_get_child(froRing[i], 0);
    if (g) {
      String gl = sh.substring(0, 1);
      lv_label_set_text(g, gl.c_str());
    }
  }
  if (uiFroStatus) {
    char buf[40];
    if (!n) lv_label_set_text(uiFroStatus, "buscando a frota");
    else {
      snprintf(buf, sizeof(buf), "%d no ar   %d na frota", live, n);
      lv_label_set_text(uiFroStatus, buf);
    }
  }
}

static void frota_anim(lv_timer_t* t) {
  (void)t;
  if (page != Frota || !uiFrota || lv_obj_has_flag(uiFrota, LV_OBJ_FLAG_HIDDEN)) return;
  crewPhase++;
  for (int p = 0; p < 6; p++) {
    if (!uiTickDot[p]) continue;
    int x = (crewPhase * 3 + p * 54) % 328 - 4;
    lv_obj_set_x(uiTickDot[p], x);
    lv_obj_set_style_bg_color(uiTickDot[p], lv_color_hex(working ? COL_GOLD : 0x5A4A38), 0);
  }
  int n = agTotal;
  if (n > 21) n = 21;
  for (int i = 0; i < n; i++) {
    if (!froRing[i] || lv_obj_has_flag(froCell[i], LV_OBJ_FLAG_HIDDEN)) continue;
    if (agentBusy[i]) {
      lv_obj_set_style_border_width(froRing[i], (crewPhase & 1) ? 3 : 2, 0);
      lv_obj_set_style_border_color(froRing[i], lv_color_hex((crewPhase & 1) ? COL_GOLD : COL_PAPER), 0);
    }
  }
}

static void style_clear(lv_obj_t* o) {
  lv_obj_set_style_border_width(o, 0, 0);
  lv_obj_set_style_shadow_width(o, 0, 0);
  lv_obj_set_style_outline_width(o, 0, 0);
  lv_obj_set_style_pad_all(o, 0, 0);
}

static lv_obj_t* gold_btn(lv_obj_t* parent, const char* txt, lv_event_cb_t cb, void* ud, int w) {
  lv_obj_t* b = lv_btn_create(parent);
  lv_obj_set_size(b, w, 28);
  style_clear(b);
  lv_obj_set_style_bg_opa(b, LV_OPA_TRANSP, 0);
  lv_obj_set_style_radius(b, 0, 0);
  lv_obj_add_event_cb(b, cb, LV_EVENT_CLICKED, ud);
  lv_obj_t* l = lv_label_create(b);
  lv_label_set_text(l, txt);
  lv_obj_set_style_text_color(l, lv_color_hex(COL_GOLD), 0);
  lv_obj_set_style_text_font(l, &lv_font_montserrat_14, 0);
  lv_obj_center(l);
  lv_obj_t* line = lv_obj_create(b);
  lv_obj_set_size(line, w - 16, 2);
  lv_obj_align(line, LV_ALIGN_BOTTOM_MID, 0, 0);
  style_clear(line);
  lv_obj_set_style_bg_color(line, lv_color_hex(COL_GOLD), 0);
  lv_obj_set_style_radius(line, 1, 0);
  lv_obj_clear_flag(line, LV_OBJ_FLAG_CLICKABLE);
  return b;
}

static lv_obj_t* make_card(lv_obj_t* p, int w, int h) {
  lv_obj_t* c = lv_obj_create(p);
  lv_obj_set_size(c, w, h);
  style_clear(c);
  lv_obj_set_style_radius(c, 12, 0);
  lv_obj_set_style_bg_color(c, lv_color_hex(COL_TILE), 0);
  lv_obj_set_style_bg_opa(c, LV_OPA_COVER, 0);
  lv_obj_set_style_pad_left(c, 12, 0);
  lv_obj_set_style_pad_right(c, 10, 0);
  lv_obj_set_style_pad_top(c, 8, 0);
  lv_obj_set_style_pad_bottom(c, 8, 0);
  lv_obj_clear_flag(c, LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_t* bar = lv_obj_create(c);
  lv_obj_set_size(bar, 3, h - 16);
  lv_obj_align(bar, LV_ALIGN_LEFT_MID, 0, 0);
  style_clear(bar);
  lv_obj_set_style_radius(bar, 2, 0);
  lv_obj_set_style_bg_color(bar, lv_color_hex(COL_GOLD), 0);
  lv_obj_set_style_bg_opa(bar, LV_OPA_COVER, 0);
  lv_obj_clear_flag(bar, LV_OBJ_FLAG_CLICKABLE);
  return c;
}

static lv_obj_t* card_line(lv_obj_t* card, const char* txt, uint32_t col, const lv_font_t* font, int y) {
  lv_obj_t* l = lv_label_create(card);
  lv_label_set_long_mode(l, LV_LABEL_LONG_DOT);
  lv_obj_set_width(l, lv_obj_get_width(card) - 22);
  lv_label_set_text(l, txt && txt[0] ? txt : " ");
  lv_obj_set_style_text_color(l, lv_color_hex(col), 0);
  lv_obj_set_style_text_font(l, font, 0);
  lv_obj_align(l, LV_ALIGN_TOP_LEFT, 8, y);
  return l;
}

static lv_obj_t* ink(lv_obj_t* p, int x, int y, int w, int h, int r) {
  lv_obj_t* o = lv_obj_create(p);
  lv_obj_set_size(o, w, h);
  lv_obj_set_pos(o, x, y);
  style_clear(o);
  lv_obj_set_style_radius(o, r, 0);
  lv_obj_set_style_bg_color(o, lv_color_hex(COL_GOLD), 0);
  lv_obj_set_style_bg_opa(o, LV_OPA_COVER, 0);
  lv_obj_clear_flag(o, LV_OBJ_FLAG_CLICKABLE);
  lv_obj_clear_flag(o, LV_OBJ_FLAG_SCROLLABLE);
  return o;
}

static lv_obj_t* ring(lv_obj_t* p, int x, int y, int s, int bw) {
  lv_obj_t* o = ink(p, x, y, s, s, LV_RADIUS_CIRCLE);
  lv_obj_set_style_bg_opa(o, LV_OPA_TRANSP, 0);
  lv_obj_set_style_border_width(o, bw, 0);
  lv_obj_set_style_border_color(o, lv_color_hex(COL_GOLD), 0);
  return o;
}

static void tile_icon(lv_obj_t* t, int i) {
  lv_obj_t* box = lv_obj_create(t);
  lv_obj_set_size(box, 36, 36);
  lv_obj_align(box, LV_ALIGN_TOP_RIGHT, 2, -2);
  style_clear(box);
  lv_obj_set_style_bg_opa(box, LV_OPA_TRANSP, 0);
  lv_obj_clear_flag(box, LV_OBJ_FLAG_CLICKABLE);
  lv_obj_clear_flag(box, LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_add_flag(box, LV_OBJ_FLAG_EVENT_BUBBLE);
  if (i == 0) {
    ring(box, 6, 5, 24, 2);
    ink(box, 14, 13, 8, 8, LV_RADIUS_CIRCLE);
  } else if (i == 1) {
    ink(box, 6, 8, 24, 4, 2);
    ink(box, 6, 16, 18, 4, 2);
    ink(box, 6, 24, 12, 4, 2);
  } else if (i == 2) {
    ring(box, 6, 5, 24, 2);
    ink(box, 17, 9, 2, 10, 1);
    ink(box, 17, 17, 8, 2, 1);
  } else if (i == 3) {
    ring(box, 3, 7, 16, 2);
    ring(box, 17, 7, 16, 2);
    ring(box, 10, 17, 16, 2);
  } else if (i == 4) {
    ring(box, 10, 4, 16, 2);
    ink(box, 16, 20, 4, 7, 2);
    ink(box, 10, 26, 16, 3, 2);
  } else {
    ink(box, 6, 18, 6, 12, 2);
    ink(box, 15, 8, 6, 22, 2);
    ink(box, 24, 14, 6, 16, 2);
  }
}

static String clip(const String& s, int n) {
  if ((int)s.length() <= n) return s;
  return s.substring(0, n - 1) + ".";
}

void refreshHeader() {
  const char* hop = WiFi.status() != WL_CONNECTED ? "wifi" : viaHop == 1 ? "LAN" : viaHop == 2 ? "TS" : "NET";
  if (uiHop) lv_label_set_text(uiHop, hop);
  int t = clockSec + (int)((millis() - clockBaseMs) / 1000UL);
  t %= 86400;
  if (t < 0) t += 86400;
  char buf[8];
  snprintf(buf, sizeof(buf), "%02d:%02d", t / 3600, (t % 3600) / 60);
  if (uiClock) lv_label_set_text(uiClock, buf);
}

void refreshTiles() {
  if (!tileVal[0]) return;
  lv_label_set_text(tileVal[0], nowK ? clip(nowTitle, 22).c_str() : "nada agora");
  char fila[24];
  snprintf(fila, sizeof(fila), "%d recados", alerts);
  lv_label_set_text(tileVal[1], fila);
  lv_label_set_text(tileVal[2], nextEvent.length() ? clip(nextEvent, 22).c_str() : "agenda livre");
  char fro[24];
  snprintf(fro, sizeof(fro), "%d no ar", working ? working : agTotal);
  lv_label_set_text(tileVal[3], fro);
  lv_label_set_text(tileVal[4], askA.length() ? clip(askA, 22).c_str() : "posso falar do dia");
  char dia[24];
  snprintf(dia, sizeof(dia), "%d fila  %d hoje", alerts, kpi[1]);
  lv_label_set_text(tileVal[5], dia);
  refreshHeader();
}

void showHome();
void showPage(Page p);
void fillPage(Page p);
static void agent_cb(lv_event_t* e);

static Page navPage = Home;
static bool navHome = false;
static bool navBusy = false;

static void nav_run(void* /*unused*/) {
  navBusy = false;
  if (navHome) showHome();
  else showPage(navPage);
}

static void go_page(Page p) {
  navHome = false;
  navPage = p;
  if (navBusy) return;
  navBusy = true;
  lv_async_call(nav_run, nullptr);
}

static void go_home() {
  navHome = true;
  if (navBusy) return;
  navBusy = true;
  lv_async_call(nav_run, nullptr);
}

static void dia_go(lv_event_t* e) {
  int i = (int)(intptr_t)lv_event_get_user_data(e);
  if (i == 0) go_page(Fila);
  else if (i == 1) go_page(Hoje);
  else go_page(Frota);
}

static int clamp_pct(int v, int cap) {
  if (cap < 1) cap = 1;
  int p = (v * 100) / cap;
  if (p < 0) p = 0;
  if (p > 100) p = 100;
  return p;
}

static void arc_run(lv_obj_t* arc, int v) {
  lv_anim_t a;
  lv_anim_init(&a);
  lv_anim_set_var(&a, arc);
  lv_anim_set_exec_cb(&a, (lv_anim_exec_xcb_t)lv_arc_set_value);
  lv_anim_set_values(&a, 0, v);
  lv_anim_set_time(&a, 650);
  lv_anim_set_path_cb(&a, lv_anim_path_ease_out);
  lv_anim_start(&a);
}

static bool diaBuilt = false;

void ensureDia() {
  if (diaArc[0] || !uiDia) return;
  static const char* caps[3] = {"fila", "hoje", "no ar"};
  for (int i = 0; i < 3; i++) {
    lv_obj_t* arc = lv_arc_create(uiDia);
    diaArc[i] = arc;
    lv_obj_set_size(arc, 86, 86);
    lv_obj_set_pos(arc, 20 + i * 100, 0);
    lv_arc_set_rotation(arc, 135);
    lv_arc_set_bg_angles(arc, 0, 270);
    lv_arc_set_range(arc, 0, 100);
    lv_arc_set_value(arc, 0);
    lv_obj_set_style_arc_width(arc, 8, LV_PART_MAIN);
    lv_obj_set_style_arc_width(arc, 8, LV_PART_INDICATOR);
    lv_obj_set_style_arc_color(arc, lv_color_hex(0x3A3024), LV_PART_MAIN);
    lv_obj_set_style_arc_color(arc, lv_color_hex(COL_GOLD), LV_PART_INDICATOR);
    lv_obj_set_style_arc_rounded(arc, true, LV_PART_MAIN);
    lv_obj_set_style_arc_rounded(arc, true, LV_PART_INDICATOR);
    lv_obj_set_style_opa(arc, LV_OPA_0, LV_PART_KNOB);
    lv_obj_add_event_cb(arc, dia_go, LV_EVENT_CLICKED, (void*)(intptr_t)i);

    lv_obj_t* num = lv_label_create(uiDia);
    diaNum[i] = num;
    lv_label_set_text(num, "0");
    lv_obj_set_style_text_color(num, lv_color_hex(COL_GOLD), 0);
    lv_obj_set_style_text_font(num, &lv_font_montserrat_20, 0);
    lv_obj_set_pos(num, 48 + i * 100, 28);

    lv_obj_t* cap = lv_label_create(uiDia);
    diaCap[i] = cap;
    lv_label_set_text(cap, caps[i]);
    lv_obj_set_style_text_color(cap, lv_color_hex(COL_MUTED), 0);
    lv_obj_set_pos(cap, 42 + i * 100, 78);
  }

  for (int i = 0; i < 5; i++) {
    lv_obj_t* track = lv_obj_create(uiDia);
    diaBar[i] = track;
    lv_obj_set_size(track, 22, 52);
    lv_obj_set_pos(track, 22 + i * 60, 100);
    style_clear(track);
    lv_obj_set_style_radius(track, 6, 0);
    lv_obj_set_style_bg_color(track, lv_color_hex(0x3A3024), 0);
    lv_obj_set_style_bg_opa(track, LV_OPA_COVER, 0);
    lv_obj_clear_flag(track, LV_OBJ_FLAG_SCROLLABLE);

    lv_obj_t* fill = lv_obj_create(track);
    diaBarFill[i] = fill;
    lv_obj_set_size(fill, 22, 6);
    lv_obj_align(fill, LV_ALIGN_BOTTOM_MID, 0, 0);
    style_clear(fill);
    lv_obj_set_style_radius(fill, 6, 0);
    lv_obj_set_style_bg_color(fill, lv_color_hex(COL_GOLD), 0);
    lv_obj_set_style_bg_opa(fill, LV_OPA_COVER, 0);
    lv_obj_clear_flag(fill, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_clear_flag(fill, LV_OBJ_FLAG_SCROLLABLE);

    lv_obj_t* lab = lv_label_create(uiDia);
    diaBarLab[i] = lab;
    lv_label_set_text(lab, "");
    lv_obj_set_style_text_color(lab, lv_color_hex(COL_MUTED), 0);
    lv_obj_set_pos(lab, 18 + i * 60, 154);

    lv_obj_t* val = lv_label_create(uiDia);
    diaBarVal[i] = val;
    lv_label_set_text(val, "");
    lv_obj_set_style_text_color(val, lv_color_hex(COL_PAPER), 0);
    lv_obj_set_pos(val, 24 + i * 60, 86);
  }

  diaFoot = lv_label_create(uiDia);
  lv_label_set_text(diaFoot, "");
  lv_obj_set_style_text_color(diaFoot, lv_color_hex(COL_MUTED), 0);
  lv_obj_set_pos(diaFoot, 10, 154);
  lv_obj_add_flag(diaFoot, LV_OBJ_FLAG_HIDDEN);
}

void refreshDia() {
  ensureDia();
  int filaN = alerts ? alerts : kpi[3];
  int hojeN = kpi[1];
  int liveN = working;
  int nums[3] = {filaN, hojeN, liveN};
  int caps[3] = {
    filaN > 8 ? filaN : 8,
    hojeN > 5 ? hojeN : 5,
    agTotal > 0 ? agTotal : 8
  };
  char buf[12];
  for (int i = 0; i < 3; i++) {
    snprintf(buf, sizeof(buf), "%d", nums[i]);
    lv_label_set_text(diaNum[i], buf);
    int p = clamp_pct(nums[i], caps[i]);
    if (!diaBuilt) arc_run(diaArc[i], p);
    else lv_arc_set_value(diaArc[i], p);
    uint32_t ac = (i == 0 && filaN >= 6) ? 0xE07050 : (i == 2 && kpi[5] > 0) ? 0xE07050 : COL_GOLD;
    lv_obj_set_style_text_color(diaNum[i], lv_color_hex(ac), 0);
    lv_obj_set_style_arc_color(diaArc[i], lv_color_hex(ac), LV_PART_INDICATOR);
  }

  int barV[5] = {};
  const char* barL[5] = {"proj", "hoje", "feito", "fila", "up"};
  char labBuf[5][8];
  int nbar = 5;
  if (dyCount > 0) {
    nbar = dyCount;
    if (nbar > 5) nbar = 5;
    for (int i = 0; i < nbar; i++) {
      barV[i] = dyMeet[i];
      String s = dyLab[i];
      if (s.length() > 4) s = s.substring(0, 4);
      strncpy(labBuf[i], s.c_str(), 7);
      labBuf[i][7] = 0;
      barL[i] = labBuf[i];
    }
  } else {
    barV[0] = kpi[0];
    barV[1] = kpi[1];
    barV[2] = kpi[2];
    barV[3] = kpi[3];
    barV[4] = kpi[4];
  }
  int mx = 1;
  for (int i = 0; i < nbar; i++) if (barV[i] > mx) mx = barV[i];
  for (int i = 0; i < 5; i++) {
    if (i >= nbar) {
      lv_obj_add_flag(diaBar[i], LV_OBJ_FLAG_HIDDEN);
      lv_obj_add_flag(diaBarLab[i], LV_OBJ_FLAG_HIDDEN);
      lv_obj_add_flag(diaBarVal[i], LV_OBJ_FLAG_HIDDEN);
      continue;
    }
    lv_obj_clear_flag(diaBar[i], LV_OBJ_FLAG_HIDDEN);
    lv_obj_clear_flag(diaBarLab[i], LV_OBJ_FLAG_HIDDEN);
    lv_obj_clear_flag(diaBarVal[i], LV_OBJ_FLAG_HIDDEN);
    int h = 6 + (46 * barV[i]) / mx;
    if (h > 52) h = 52;
    lv_obj_set_height(diaBarFill[i], h);
    lv_obj_align(diaBarFill[i], LV_ALIGN_BOTTOM_MID, 0, 0);
    lv_label_set_text(diaBarLab[i], barL[i]);
    snprintf(buf, sizeof(buf), "%d", barV[i]);
    lv_label_set_text(diaBarVal[i], buf);
  }

  if (diaFoot) lv_obj_add_flag(diaFoot, LV_OBJ_FLAG_HIDDEN);
  diaBuilt = true;
}

static void back_cb(lv_event_t* e) {
  (void)e;
  if (page == Agent) go_page(Frota);
  else go_home();
}

static void agent_cb(lv_event_t* e) {
  int i = (int)(intptr_t)lv_event_get_user_data(e);
  if (i < 0 || i >= agTotal) return;
  agCursor = i;
  go_page(Agent);
}

void refreshAgent();

static void ag_chip_cb(lv_event_t* e) {
  int slot = (int)(intptr_t)lv_event_get_user_data(e);
  String sh = agShort[agCursor];
  sh.toUpperCase();
  if (sh == "CTL") {
    if (slot == 0) go_page(Agora);
    else if (slot == 1) go_page(Frota);
    else go_page(Hoje);
    return;
  }
  String q = "como esta ";
  q += agName[agCursor];
  q += ", ";
  q += chipLab(agCursor, slot);
  sendAsk(agName[agCursor], q);
  refreshAgent();
}

static void ag_ask_cb(lv_event_t* e) {
  (void)e;
  String q = "o que o agente ";
  q += agName[agCursor];
  q += " tem na mesa agora";
  sendAsk(agName[agCursor], q);
  refreshAgent();
}

static void ag_item_cb(lv_event_t* e) {
  int i = (int)(intptr_t)lv_event_get_user_data(e);
  if (i < 0 || i >= listCount) return;
  nowTitle = listA[i];
  nowWho = listB[i];
  nowId = listId[i];
  nowK = listK[i];
  nowAg = agName[agCursor];
  go_page(Agora);
}

static void act_cb(lv_event_t* e) {
  int btn = (int)(intptr_t)lv_event_get_user_data(e);
  if (!nowK) return;
  beep();
  fireBtn(nowId, nowK, btn);
  skip(nowId);
  pickNow();
  fillPage(Agora);
  refreshTiles();
}

static void chip_cb(lv_event_t* e) {
  const char* q = (const char*)lv_event_get_user_data(e);
  sendAsk("orquestrador", q);
  go_page(Guia);
}

static void orb_cb(lv_event_t* e);
static void orb_listen(void* /*unused*/);

void refreshGuia() {
  if (!orbHint) return;
  const char* hint = "toque para falar";
  uint32_t halo = 0x5A4A38;
  uint32_t core = COL_GOLD;
  int bw = 2;
  if (orbMode == OrbListen) {
    hint = "pode falar";
    halo = COL_GOLD;
    bw = 4;
  } else if (orbMode == OrbThink) {
    hint = "um instante";
    halo = COL_GOLD;
    bw = 3;
  } else if (orbMode == OrbSpeak) {
    hint = "toque de novo";
    halo = COL_GOLD;
    bw = 3;
  }
  lv_label_set_text(orbHint, hint);
  lv_obj_set_style_border_color(orbHalo, lv_color_hex(halo), 0);
  lv_obj_set_style_border_width(orbHalo, bw, 0);
  lv_obj_set_style_bg_color(orbCore, lv_color_hex(core), 0);
  String said = askA;
  if (!said.length()) said = "Oi. Toque o orb e fale do seu dia.";
  lv_label_set_text(orbSaid, clip(said, 120).c_str());
}

void ensureGuia() {
  if (orbHalo || !uiGuia) return;
  orbHalo = lv_obj_create(uiGuia);
  lv_obj_set_size(orbHalo, 96, 96);
  lv_obj_set_pos(orbHalo, 112, 2);
  style_clear(orbHalo);
  lv_obj_set_style_radius(orbHalo, LV_RADIUS_CIRCLE, 0);
  lv_obj_set_style_bg_opa(orbHalo, LV_OPA_TRANSP, 0);
  lv_obj_set_style_border_width(orbHalo, 2, 0);
  lv_obj_set_style_border_color(orbHalo, lv_color_hex(0x5A4A38), 0);
  lv_obj_add_flag(orbHalo, LV_OBJ_FLAG_CLICKABLE);
  lv_obj_add_event_cb(orbHalo, orb_cb, LV_EVENT_CLICKED, nullptr);

  orbMid = lv_obj_create(orbHalo);
  lv_obj_set_size(orbMid, 72, 72);
  style_clear(orbMid);
  lv_obj_set_style_radius(orbMid, LV_RADIUS_CIRCLE, 0);
  lv_obj_set_style_bg_color(orbMid, lv_color_hex(COL_TILE2), 0);
  lv_obj_set_style_bg_opa(orbMid, LV_OPA_COVER, 0);
  lv_obj_set_style_border_width(orbMid, 2, 0);
  lv_obj_set_style_border_color(orbMid, lv_color_hex(COL_GOLD), 0);
  lv_obj_center(orbMid);
  lv_obj_clear_flag(orbMid, LV_OBJ_FLAG_CLICKABLE);

  orbCore = lv_obj_create(orbMid);
  lv_obj_set_size(orbCore, 40, 40);
  style_clear(orbCore);
  lv_obj_set_style_radius(orbCore, LV_RADIUS_CIRCLE, 0);
  lv_obj_set_style_bg_color(orbCore, lv_color_hex(COL_GOLD), 0);
  lv_obj_set_style_bg_opa(orbCore, LV_OPA_COVER, 0);
  lv_obj_center(orbCore);
  lv_obj_add_flag(orbCore, LV_OBJ_FLAG_CLICKABLE);
  lv_obj_add_event_cb(orbCore, orb_cb, LV_EVENT_CLICKED, nullptr);

  orbHint = lv_label_create(uiGuia);
  lv_label_set_text(orbHint, "toque para falar");
  lv_obj_set_style_text_color(orbHint, lv_color_hex(COL_GOLD), 0);
  lv_obj_set_style_text_font(orbHint, &lv_font_montserrat_14, 0);
  lv_obj_align(orbHint, LV_ALIGN_TOP_MID, 0, 102);

  orbSaid = lv_label_create(uiGuia);
  lv_label_set_long_mode(orbSaid, LV_LABEL_LONG_WRAP);
  lv_obj_set_width(orbSaid, 292);
  lv_label_set_text(orbSaid, "Oi. Toque o orb e fale do seu dia.");
  lv_obj_set_style_text_color(orbSaid, lv_color_hex(COL_PAPER), 0);
  lv_obj_align(orbSaid, LV_ALIGN_TOP_MID, 0, 124);
}

static void orb_listen(void* /*unused*/) {
  orbMode = OrbListen;
  refreshGuia();
  lv_refr_now(nullptr);
  String raw;
  if (viaHop == 1) raw = postJsonRet(LAN_LIS, "{}", false);
  else if (viaHop == 2) raw = postJsonRet(TS_LIS, "{}", true);
  else raw = postJsonRet(CLOUD_LIS, "{}", true);
  String heard = jsonTextField(raw);
  if (!heard.length()) {
    askA = "Nao ouvi. Toque o orb e fale de novo, com o fone no computador.";
    orbMode = OrbIdle;
    refreshGuia();
    return;
  }
  orbMode = OrbThink;
  sendAsk("orquestrador", heard);
  refreshGuia();
}

static void orb_cb(lv_event_t* e) {
  (void)e;
  if (orbMode == OrbListen || orbMode == OrbThink) return;
  orbMode = OrbListen;
  refreshGuia();
  lv_async_call(orb_listen, nullptr);
}

static void guia_anim(lv_timer_t* t) {
  (void)t;
  if (page != Guia || !orbHalo || lv_obj_has_flag(uiGuia, LV_OBJ_FLAG_HIDDEN)) return;
  orbPhase++;
  int opa = 70;
  int core = 40;
  if (orbMode == OrbIdle) {
    opa = 50 + ((orbPhase & 8) ? 40 : 0);
    core = 38 + ((orbPhase & 8) ? 4 : 0);
  } else if (orbMode == OrbListen) {
    opa = 255;
    core = 44 + ((orbPhase & 2) ? 6 : 0);
  } else if (orbMode == OrbThink) {
    opa = (orbPhase & 2) ? 255 : 80;
    core = 40;
  } else {
    opa = 180 + ((orbPhase & 4) ? 70 : 0);
    core = 42;
  }
  lv_obj_set_style_border_opa(orbHalo, opa, 0);
  lv_obj_set_size(orbCore, core, core);
  lv_obj_center(orbCore);
}

static void count_agent(int& nIn, int& nTk, int& nEv) {
  nIn = nTk = nEv = 0;
  String want = agName[agCursor];
  for (int i = 1; i <= 8; i++) {
    String row = field(ctrlBody, "IN" + String(i));
    if (row.length() && pipe(row, 0) == want) nIn++;
    row = field(ctrlBody, "TK" + String(i));
    if (row.length() && pipe(row, 0) == want) nTk++;
    if (i <= 6) {
      row = field(ctrlBody, "EV" + String(i));
      if (row.length() && pipe(row, 0) == want) nEv++;
    }
  }
}

void ensureAgent() {
  if (agAvatar || !uiAgent) return;
  agAvatar = lv_obj_create(uiAgent);
  lv_obj_set_size(agAvatar, 36, 36);
  lv_obj_set_pos(agAvatar, 10, 4);
  style_clear(agAvatar);
  lv_obj_set_style_radius(agAvatar, LV_RADIUS_CIRCLE, 0);
  lv_obj_set_style_bg_color(agAvatar, lv_color_hex(COL_TILE), 0);
  lv_obj_set_style_bg_opa(agAvatar, LV_OPA_COVER, 0);
  lv_obj_set_style_border_width(agAvatar, 2, 0);
  lv_obj_set_style_border_color(agAvatar, lv_color_hex(COL_GOLD), 0);
  lv_obj_t* gl = lv_label_create(agAvatar);
  lv_label_set_text(gl, "A");
  lv_obj_set_style_text_color(gl, lv_color_hex(COL_GOLD), 0);
  lv_obj_center(gl);

  agNameL = lv_label_create(uiAgent);
  lv_label_set_long_mode(agNameL, LV_LABEL_LONG_DOT);
  lv_obj_set_width(agNameL, 200);
  lv_obj_set_pos(agNameL, 54, 4);
  lv_obj_set_style_text_color(agNameL, lv_color_hex(COL_PAPER), 0);
  lv_obj_set_style_text_font(agNameL, &lv_font_montserrat_20, 0);

  agMetaL = lv_label_create(uiAgent);
  lv_obj_set_pos(agMetaL, 54, 26);
  lv_obj_set_style_text_color(agMetaL, lv_color_hex(COL_GOLD), 0);

  agArc = lv_arc_create(uiAgent);
  lv_obj_set_size(agArc, 52, 52);
  lv_obj_set_pos(agArc, 8, 46);
  lv_arc_set_rotation(agArc, 135);
  lv_arc_set_bg_angles(agArc, 0, 270);
  lv_arc_set_range(agArc, 0, 100);
  lv_obj_set_style_arc_width(agArc, 6, LV_PART_MAIN);
  lv_obj_set_style_arc_width(agArc, 6, LV_PART_INDICATOR);
  lv_obj_set_style_arc_color(agArc, lv_color_hex(0x3A3024), LV_PART_MAIN);
  lv_obj_set_style_arc_color(agArc, lv_color_hex(COL_GOLD), LV_PART_INDICATOR);
  lv_obj_set_style_opa(agArc, LV_OPA_0, LV_PART_KNOB);
  lv_obj_clear_flag(agArc, LV_OBJ_FLAG_CLICKABLE);
  agArcN = lv_label_create(uiAgent);
  lv_label_set_text(agArcN, "0");
  lv_obj_set_style_text_color(agArcN, lv_color_hex(COL_GOLD), 0);
  lv_obj_set_pos(agArcN, 24, 62);

  static const char* blab[3] = {"rec", "tar", "age"};
  for (int i = 0; i < 3; i++) {
    agBar[i] = lv_obj_create(uiAgent);
    lv_obj_set_size(agBar[i], 18, 40);
    lv_obj_set_pos(agBar[i], 70 + i * 48, 52);
    style_clear(agBar[i]);
    lv_obj_set_style_radius(agBar[i], 4, 0);
    lv_obj_set_style_bg_color(agBar[i], lv_color_hex(0x3A3024), 0);
    lv_obj_set_style_bg_opa(agBar[i], LV_OPA_COVER, 0);
    lv_obj_clear_flag(agBar[i], LV_OBJ_FLAG_SCROLLABLE);
    agBarFill[i] = lv_obj_create(agBar[i]);
    lv_obj_set_size(agBarFill[i], 18, 6);
    lv_obj_align(agBarFill[i], LV_ALIGN_BOTTOM_MID, 0, 0);
    style_clear(agBarFill[i]);
    lv_obj_set_style_radius(agBarFill[i], 4, 0);
    lv_obj_set_style_bg_color(agBarFill[i], lv_color_hex(COL_GOLD), 0);
    lv_obj_set_style_bg_opa(agBarFill[i], LV_OPA_COVER, 0);
    lv_obj_clear_flag(agBarFill[i], LV_OBJ_FLAG_CLICKABLE);
    agBarVal[i] = lv_label_create(uiAgent);
    lv_label_set_text(agBarVal[i], "0");
    lv_obj_set_style_text_color(agBarVal[i], lv_color_hex(COL_PAPER), 0);
    lv_obj_set_pos(agBarVal[i], 72 + i * 48, 42);
    agBarLab[i] = lv_label_create(uiAgent);
    lv_label_set_text(agBarLab[i], blab[i]);
    lv_obj_set_style_text_color(agBarLab[i], lv_color_hex(COL_MUTED), 0);
    lv_obj_set_pos(agBarLab[i], 70 + i * 48, 94);
  }

  lv_obj_t* chips = lv_obj_create(uiAgent);
  lv_obj_set_size(chips, 300, 28);
  lv_obj_set_pos(chips, 8, 108);
  style_clear(chips);
  lv_obj_set_style_bg_opa(chips, LV_OPA_TRANSP, 0);
  lv_obj_set_flex_flow(chips, LV_FLEX_FLOW_ROW);
  lv_obj_set_style_pad_gap(chips, 8, 0);
  gold_btn(chips, "mesa", ag_chip_cb, (void*)(intptr_t)0, 70);
  gold_btn(chips, "foco", ag_chip_cb, (void*)(intptr_t)1, 70);
  gold_btn(chips, "hoje", ag_chip_cb, (void*)(intptr_t)2, 70);
  gold_btn(chips, "falar", ag_ask_cb, nullptr, 70);

  agNoteL = lv_label_create(uiAgent);
  lv_label_set_long_mode(agNoteL, LV_LABEL_LONG_WRAP);
  lv_obj_set_width(agNoteL, 300);
  lv_obj_set_pos(agNoteL, 10, 136);
  lv_obj_set_style_text_color(agNoteL, lv_color_hex(COL_PAPER), 0);

  agScroll = lv_obj_create(uiAgent);
  lv_obj_set_size(agScroll, 304, 36);
  lv_obj_set_pos(agScroll, 8, 136);
  style_clear(agScroll);
  lv_obj_set_style_bg_opa(agScroll, LV_OPA_TRANSP, 0);
  lv_obj_set_flex_flow(agScroll, LV_FLEX_FLOW_COLUMN);
  lv_obj_set_style_pad_gap(agScroll, 4, 0);
  lv_obj_set_scroll_dir(agScroll, LV_DIR_VER);
  lv_obj_add_flag(agScroll, LV_OBJ_FLAG_HIDDEN);
}

void refreshAgent() {
  ensureAgent();
  if (!agNameL) return;
  loadAgentItems();
  String sh = agShort[agCursor];
  sh.toUpperCase();
  lv_label_set_text(agNameL, agName[agCursor].c_str());
  lv_obj_t* gl = lv_obj_get_child(agAvatar, 0);
  if (gl) lv_label_set_text(gl, sh.substring(0, 1).c_str());
  lv_obj_set_style_border_color(agAvatar, lv_color_hex(agentBusy[agCursor] ? COL_GOLD : 0x5A4A38), 0);
  String meta = agTeam[agCursor];
  meta += agentBusy[agCursor] ? "  ao vivo" : "  espera";
  lv_label_set_text(agMetaL, meta.c_str());
  lv_obj_set_style_text_color(agMetaL, lv_color_hex(agentBusy[agCursor] ? COL_GOLD : COL_MUTED), 0);

  int nIn, nTk, nEv;
  count_agent(nIn, nTk, nEv);
  int load = agLoad[agCursor];
  if (load < nIn + nTk + nEv) load = nIn + nTk + nEv;
  char buf[8];
  snprintf(buf, sizeof(buf), "%d", load);
  lv_label_set_text(agArcN, buf);
  int cap = load > 6 ? load : 6;
  lv_arc_set_value(agArc, clamp_pct(load, cap));
  int vals[3] = {nIn, nTk, nEv};
  int mx = 1;
  for (int i = 0; i < 3; i++) if (vals[i] > mx) mx = vals[i];
  for (int i = 0; i < 3; i++) {
    int h = 6 + (34 * vals[i]) / mx;
    if (h > 40) h = 40;
    lv_obj_set_height(agBarFill[i], h);
    lv_obj_align(agBarFill[i], LV_ALIGN_BOTTOM_MID, 0, 0);
    snprintf(buf, sizeof(buf), "%d", vals[i]);
    lv_label_set_text(agBarVal[i], buf);
  }

  String note = agHead[agCursor].length() ? agHead[agCursor] : agRole[agCursor];
  if (askA.length() && askAg == agName[agCursor]) note = askA;
  if (!note.length()) note = agAct[agCursor].length() ? agAct[agCursor] : "Toque mesa, foco ou hoje.";
  lv_label_set_text(agNoteL, clip(note, 90).c_str());

  bool showAsk = askPending && askAg == agName[agCursor];
  lv_obj_clean(agScroll);
  if (listCount && !showAsk) {
    lv_obj_clear_flag(agScroll, LV_OBJ_FLAG_HIDDEN);
    lv_obj_add_flag(agNoteL, LV_OBJ_FLAG_HIDDEN);
    for (int i = 0; i < listCount && i < 4; i++) {
      lv_obj_t* card = make_card(agScroll, 300, 32);
      lv_obj_add_flag(card, LV_OBJ_FLAG_CLICKABLE);
      lv_obj_add_event_cb(card, ag_item_cb, LV_EVENT_CLICKED, (void*)(intptr_t)i);
      card_line(card, clip(listA[i], 34).c_str(), COL_PAPER, &lv_font_montserrat_14, 2);
    }
  } else {
    lv_obj_add_flag(agScroll, LV_OBJ_FLAG_HIDDEN);
    lv_obj_clear_flag(agNoteL, LV_OBJ_FLAG_HIDDEN);
  }
}

void fillPage(Page p) {
  page = p;
  lv_obj_clean(uiPageBody);
  if (uiActBar) {
    lv_obj_add_flag(uiActBar, LV_OBJ_FLAG_HIDDEN);
  }
  const char* titles[] = {"", "agora", "fila", "hoje", "frota", "guia", "o dia", "agente"};
  lv_label_set_text(uiPageTitle, p == Agent && agShort[agCursor].length() ? agShort[agCursor].c_str() : titles[p]);
  if (uiFrota) {
    if (p == Frota) lv_obj_clear_flag(uiFrota, LV_OBJ_FLAG_HIDDEN);
    else lv_obj_add_flag(uiFrota, LV_OBJ_FLAG_HIDDEN);
  }
  if (uiDia) {
    if (p == Dia) lv_obj_clear_flag(uiDia, LV_OBJ_FLAG_HIDDEN);
    else lv_obj_add_flag(uiDia, LV_OBJ_FLAG_HIDDEN);
  }
  if (uiGuia) {
    if (p == Guia) lv_obj_clear_flag(uiGuia, LV_OBJ_FLAG_HIDDEN);
    else lv_obj_add_flag(uiGuia, LV_OBJ_FLAG_HIDDEN);
  }
  if (uiAgent) {
    if (p == Agent) lv_obj_clear_flag(uiAgent, LV_OBJ_FLAG_HIDDEN);
    else lv_obj_add_flag(uiAgent, LV_OBJ_FLAG_HIDDEN);
  }
  if (uiPageBody) {
    if (p == Frota || p == Dia || p == Guia || p == Agent) lv_obj_add_flag(uiPageBody, LV_OBJ_FLAG_HIDDEN);
    else lv_obj_clear_flag(uiPageBody, LV_OBJ_FLAG_HIDDEN);
  }

  if (p == Agora) {
    lv_obj_t* card = make_card(uiPageBody, 300, 88);
    if (!nowK) {
      card_line(card, "nada agora", COL_GOLD, &lv_font_montserrat_14, 2);
      card_line(card, "A fila esta em paz. Nada pedindo voce.", COL_MUTED, &lv_font_montserrat_14, 24);
    } else {
      card_line(card, nowTitle.c_str(), COL_PAPER, &lv_font_montserrat_14, 2);
      String who = nowWho;
      if (nowAg.length()) {
        if (who.length()) who += "  ·  ";
        who += nowAg;
      }
      card_line(card, who.c_str(), COL_MUTED, &lv_font_montserrat_14, 40);
      if (uiActBar) lv_obj_clear_flag(uiActBar, LV_OBJ_FLAG_HIDDEN);
    }
  } else if (p == Fila) {
    int n = 0;
    for (int i = 1; i <= 8; i++) {
      String row = field(ctrlBody, "IN" + String(i));
      if (!row.length()) break;
      String id = pipe(row, 3);
      if (skipped(id)) continue;
      lv_obj_t* card = make_card(uiPageBody, 300, 48);
      card_line(card, clip(pipe(row, 1), 36).c_str(), COL_PAPER, &lv_font_montserrat_14, 0);
      card_line(card, pipe(row, 2).c_str(), COL_MUTED, &lv_font_montserrat_14, 22);
      n++;
    }
    if (!n) {
      lv_obj_t* card = make_card(uiPageBody, 300, 56);
      card_line(card, "fila vazia", COL_GOLD, &lv_font_montserrat_14, 2);
      card_line(card, "Sem recados na mesa agora.", COL_MUTED, &lv_font_montserrat_14, 24);
    }
  } else if (p == Hoje) {
    lv_obj_t* c1 = make_card(uiPageBody, 300, 52);
    card_line(c1, "hoje", COL_GOLD, &lv_font_montserrat_14, 0);
    card_line(c1, hoje.length() ? clip(hoje, 40).c_str() : "Nada marcado para hoje.", COL_PAPER, &lv_font_montserrat_14, 22);
    if (nextEvent.length()) {
      lv_obj_t* c2 = make_card(uiPageBody, 300, 52);
      card_line(c2, "proximo", COL_GOLD, &lv_font_montserrat_14, 0);
      card_line(c2, clip(nextEvent, 40).c_str(), COL_PAPER, &lv_font_montserrat_14, 22);
    }
    if (mit.length()) {
      lv_obj_t* c3 = make_card(uiPageBody, 300, 52);
      card_line(c3, "foco", COL_GOLD, &lv_font_montserrat_14, 0);
      card_line(c3, clip(mit, 40).c_str(), COL_MUTED, &lv_font_montserrat_14, 22);
    }
    if (futuro.length()) {
      lv_obj_t* c4 = make_card(uiPageBody, 300, 48);
      card_line(c4, "depois", COL_GOLD, &lv_font_montserrat_14, 0);
      card_line(c4, clip(futuro, 40).c_str(), COL_MUTED, &lv_font_montserrat_14, 22);
    }
  } else if (p == Frota) {
    refreshFrota();
  } else if (p == Agent) {
    refreshAgent();
  } else if (p == Guia) {
    ensureGuia();
    if (orbMode == OrbIdle && !askA.length())
      askA = "Oi. Toque o orb e fale do seu dia.";
    refreshGuia();
  } else if (p == Dia) {
    refreshDia();
  }
}

void showHome() {
  page = Home;
  lv_obj_clear_flag(uiGrid, LV_OBJ_FLAG_HIDDEN);
  lv_obj_add_flag(uiPage, LV_OBJ_FLAG_HIDDEN);
  if (uiFrota) lv_obj_add_flag(uiFrota, LV_OBJ_FLAG_HIDDEN);
  if (uiDia) lv_obj_add_flag(uiDia, LV_OBJ_FLAG_HIDDEN);
  if (uiGuia) lv_obj_add_flag(uiGuia, LV_OBJ_FLAG_HIDDEN);
  if (uiAgent) lv_obj_add_flag(uiAgent, LV_OBJ_FLAG_HIDDEN);
  refreshTiles();
}

void showPage(Page p) {
  lv_obj_add_flag(uiGrid, LV_OBJ_FLAG_HIDDEN);
  lv_obj_clear_flag(uiPage, LV_OBJ_FLAG_HIDDEN);
  fillPage(p);
}

static void tile_cb(lv_event_t* e) {
  int i = (int)(intptr_t)lv_event_get_user_data(e);
  if (i < 0 || i > 5) return;
  static const Page pages[] = {Agora, Fila, Hoje, Frota, Guia, Dia};
  go_page(pages[i]);
}

void flush_cb(lv_disp_drv_t* disp, const lv_area_t* area, lv_color_t* color_p) {
  uint32_t w = (area->x2 - area->x1 + 1);
  uint32_t h = (area->y2 - area->y1 + 1);
  tft.startWrite();
  tft.setAddrWindow(area->x1, area->y1, w, h);
  tft.writePixels((uint16_t*)color_p, w * h, true, false);
  tft.endWrite();
  lv_disp_flush_ready(disp);
}

static void touchBusBegin() {
  pinMode(Pins::touchMosi, OUTPUT);
  pinMode(Pins::touchMiso, INPUT);
  pinMode(Pins::touchSclk, OUTPUT);
  pinMode(Pins::touchCs, OUTPUT);
  digitalWrite(Pins::touchCs, HIGH);
  digitalWrite(Pins::touchSclk, LOW);
  digitalWrite(Pins::touchMosi, LOW);
}

static void tWrite(uint8_t command) {
  for (int i = 7; i >= 0; i--) {
    digitalWrite(Pins::touchMosi, (command >> i) & 1);
    digitalWrite(Pins::touchSclk, LOW);
    delayMicroseconds(2);
    digitalWrite(Pins::touchSclk, HIGH);
    delayMicroseconds(2);
  }
  digitalWrite(Pins::touchSclk, LOW);
  digitalWrite(Pins::touchMosi, LOW);
}

static uint16_t tReadCmd(uint8_t command) {
  tWrite(command);
  uint16_t result = 0;
  for (int i = 15; i >= 0; i--) {
    digitalWrite(Pins::touchSclk, HIGH);
    delayMicroseconds(2);
    digitalWrite(Pins::touchSclk, LOW);
    delayMicroseconds(2);
    result |= (uint16_t)digitalRead(Pins::touchMiso) << i;
  }
  return result >> 4;
}

static void readPanel(int& x, int& y, int& z) {
  digitalWrite(Pins::touchCs, LOW);
  uint16_t z1 = tReadCmd(0xB1);
  uint16_t z2 = tReadCmd(0xC1);
  uint16_t xr = tReadCmd(0x91);
  uint16_t yr = tReadCmd(0xD0);
  digitalWrite(Pins::touchCs, HIGH);
  int pressure = (int)z1 + 4095 - (int)z2;
  if (pressure < 0) pressure = 0;
  x = xr;
  y = yr;
  z = pressure;
}

static bool fingerRaw(int x, int y, int z) {
  if (z < 220) return false;
  if (x < 150 || y < 150 || x > 3950 || y > 3950) return false;
  return true;
}

static bool loadTouchCal() {
  nvs_handle_t h;
  if (nvs_open("control", NVS_READONLY, &h) != ESP_OK) return false;
  int32_t v = 0;
  bool have = nvs_get_i32(h, "tl4", &v) == ESP_OK;
  if (have) {
    touchL = v;
    if (nvs_get_i32(h, "tr4", &v) == ESP_OK) touchR = v;
    if (nvs_get_i32(h, "tt4", &v) == ESP_OK) touchT = v;
    if (nvs_get_i32(h, "tb4", &v) == ESP_OK) touchB = v;
    if (nvs_get_i32(h, "tsw4", &v) == ESP_OK) touchSwap = v;
  }
  nvs_close(h);
  return have;
}

static void mapRaw(int rx, int ry, int& sx, int& sy) {
  int ax = touchSwap ? ry : rx;
  int ay = touchSwap ? rx : ry;
  sx = constrain(map(ax, touchL, touchR, outL, outR), 0, (int)screenW - 1);
  sy = constrain(map(ay, touchT, touchB, outT, outB), 0, (int)screenH - 1);
}

void touch_cb(lv_indev_drv_t* drv, lv_indev_data_t* data) {
  (void)drv;
  static int sx = -1, sy = -1;
  static int hold = 0;
  static int lastX = 0, lastY = 0;
  int rawX, rawY, rawZ;
  readPanel(rawX, rawY, rawZ);
  bool near = hold > 0 && abs(rawX - lastX) + abs(rawY - lastY) < 140;
  if (!fingerRaw(rawX, rawY, rawZ) || (hold > 0 && !near)) {
    hold = 0;
    sx = -1;
    data->state = LV_INDEV_STATE_REL;
    return;
  }
  lastX = rawX;
  lastY = rawY;
  hold++;
  if (hold < 3) {
    data->state = LV_INDEV_STATE_REL;
    return;
  }
  int x, y;
  mapRaw(rawX, rawY, x, y);
  if (sx >= 0 && abs(x - sx) + abs(y - sy) > 28) {
    hold = 0;
    sx = -1;
    data->state = LV_INDEV_STATE_REL;
    return;
  }
  if (sx < 0) Serial.printf("toque %d,%d z=%d\n", x, y, rawZ);
  sx = x;
  sy = y;
  data->state = LV_INDEV_STATE_PR;
  data->point.x = (lv_coord_t)sx;
  data->point.y = (lv_coord_t)sy;
}

void ui_create() {
  lv_obj_t* scr = lv_scr_act();
  lv_obj_set_style_bg_color(scr, lv_color_hex(COL_BG), 0);
  lv_obj_set_style_bg_opa(scr, LV_OPA_COVER, 0);

  uiBar = lv_obj_create(scr);
  lv_obj_set_size(uiBar, 320, 36);
  lv_obj_set_pos(uiBar, 0, 0);
  style_clear(uiBar);
  lv_obj_set_style_bg_color(uiBar, lv_color_hex(COL_BAR), 0);
  lv_obj_set_style_bg_opa(uiBar, LV_OPA_COVER, 0);

  lv_obj_t* mark = lv_obj_create(uiBar);
  lv_obj_set_size(mark, 22, 22);
  lv_obj_set_pos(mark, 8, 7);
  style_clear(mark);
  lv_obj_set_style_radius(mark, LV_RADIUS_CIRCLE, 0);
  lv_obj_set_style_bg_color(mark, lv_color_hex(COL_GOLD), 0);
  lv_obj_set_style_bg_opa(mark, LV_OPA_COVER, 0);
  lv_obj_add_flag(mark, LV_OBJ_FLAG_CLICKABLE);
  lv_obj_add_event_cb(mark, back_cb, LV_EVENT_CLICKED, nullptr);
  lv_obj_t* c = lv_label_create(mark);
  lv_label_set_text(c, "C");
  lv_obj_set_style_text_color(c, lv_color_hex(COL_INK), 0);
  lv_obj_center(c);

  lv_obj_t* title = lv_label_create(uiBar);
  lv_label_set_text(title, "CONTROL");
  lv_obj_set_style_text_color(title, lv_color_hex(COL_PAPER), 0);
  lv_obj_set_style_text_font(title, &lv_font_montserrat_14, 0);
  lv_obj_align(title, LV_ALIGN_LEFT_MID, 38, 0);

  uiHop = lv_label_create(uiBar);
  lv_label_set_text(uiHop, "...");
  lv_obj_set_style_text_color(uiHop, lv_color_hex(COL_GOLD), 0);
  lv_obj_align(uiHop, LV_ALIGN_RIGHT_MID, -58, 0);

  uiClock = lv_label_create(uiBar);
  lv_label_set_text(uiClock, "--:--");
  lv_obj_set_style_text_color(uiClock, lv_color_hex(COL_MUTED), 0);
  lv_obj_align(uiClock, LV_ALIGN_RIGHT_MID, -10, 0);

  static lv_coord_t cols[] = {148, 148, LV_GRID_TEMPLATE_LAST};
  static lv_coord_t rows[] = {58, 58, 58, LV_GRID_TEMPLATE_LAST};
  uiGrid = lv_obj_create(scr);
  lv_obj_set_size(uiGrid, 320, 204);
  lv_obj_set_pos(uiGrid, 0, 36);
  style_clear(uiGrid);
  lv_obj_set_style_bg_opa(uiGrid, LV_OPA_TRANSP, 0);
  lv_obj_set_style_pad_all(uiGrid, 8, 0);
  lv_obj_set_style_pad_gap(uiGrid, 8, 0);
  lv_obj_set_layout(uiGrid, LV_LAYOUT_GRID);
  lv_obj_set_grid_dsc_array(uiGrid, cols, rows);

  static const char* tileTitle[6] = {"agora", "fila", "hoje", "frota", "guia", "o dia"};
  const uint32_t pastel[6] = {COL_TILE2, COL_TILE, COL_TILE, COL_TILE, COL_TILE2, COL_TILE};
  for (int i = 0; i < 6; i++) {
    lv_obj_t* t = lv_btn_create(uiGrid);
    lv_obj_set_grid_cell(t, LV_GRID_ALIGN_STRETCH, i % 2, 1, LV_GRID_ALIGN_STRETCH, i / 2, 1);
    style_clear(t);
    lv_obj_set_style_bg_color(t, lv_color_hex(pastel[i]), 0);
    lv_obj_set_style_bg_opa(t, LV_OPA_COVER, 0);
    lv_obj_set_style_radius(t, 14, 0);
    lv_obj_set_style_pad_all(t, 10, 0);
    lv_obj_set_style_pad_right(t, 40, 0);
    lv_obj_add_event_cb(t, tile_cb, LV_EVENT_CLICKED, (void*)(intptr_t)i);

    lv_obj_t* a = lv_label_create(t);
    lv_label_set_text(a, tileTitle[i]);
    lv_obj_set_style_text_color(a, lv_color_hex(COL_GOLD), 0);
    lv_obj_set_style_text_font(a, &lv_font_montserrat_14, 0);
    lv_obj_align(a, LV_ALIGN_TOP_LEFT, 0, 0);
    tile_icon(t, i);

    tileVal[i] = lv_label_create(t);
    lv_label_set_text(tileVal[i], "...");
    lv_obj_set_style_text_color(tileVal[i], lv_color_hex(COL_PAPER), 0);
    lv_obj_align(tileVal[i], LV_ALIGN_BOTTOM_LEFT, 0, 0);
  }

  uiPage = lv_obj_create(scr);
  lv_obj_set_size(uiPage, 320, 204);
  lv_obj_set_pos(uiPage, 0, 36);
  style_clear(uiPage);
  lv_obj_set_style_bg_color(uiPage, lv_color_hex(COL_BG), 0);
  lv_obj_set_style_bg_opa(uiPage, LV_OPA_COVER, 0);
  lv_obj_add_flag(uiPage, LV_OBJ_FLAG_HIDDEN);

  lv_obj_t* back = gold_btn(uiPage, "voltar", back_cb, nullptr, 80);
  lv_obj_set_pos(back, 8, 4);

  uiPageTitle = lv_label_create(uiPage);
  lv_label_set_text(uiPageTitle, "");
  lv_obj_set_style_text_color(uiPageTitle, lv_color_hex(COL_GOLD), 0);
  lv_obj_set_style_text_font(uiPageTitle, &lv_font_montserrat_20, 0);
  lv_obj_align(uiPageTitle, LV_ALIGN_TOP_LEFT, 96, 4);

  uiPageBody = lv_obj_create(uiPage);
  lv_obj_set_size(uiPageBody, 304, 160);
  lv_obj_set_pos(uiPageBody, 8, 36);
  style_clear(uiPageBody);
  lv_obj_set_style_bg_opa(uiPageBody, LV_OPA_TRANSP, 0);
  lv_obj_set_flex_flow(uiPageBody, LV_FLEX_FLOW_COLUMN);
  lv_obj_set_style_pad_gap(uiPageBody, 8, 0);
  lv_obj_set_scroll_dir(uiPageBody, LV_DIR_VER);
  lv_obj_set_scrollbar_mode(uiPageBody, LV_SCROLLBAR_MODE_AUTO);

  uiFrota = lv_obj_create(uiPage);
  lv_obj_set_size(uiFrota, 320, 172);
  lv_obj_set_pos(uiFrota, 0, 32);
  style_clear(uiFrota);
  lv_obj_set_style_bg_opa(uiFrota, LV_OPA_TRANSP, 0);
  lv_obj_clear_flag(uiFrota, LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_add_flag(uiFrota, LV_OBJ_FLAG_HIDDEN);

  uiDia = lv_obj_create(uiPage);
  lv_obj_set_size(uiDia, 320, 172);
  lv_obj_set_pos(uiDia, 0, 32);
  style_clear(uiDia);
  lv_obj_set_style_bg_opa(uiDia, LV_OPA_TRANSP, 0);
  lv_obj_clear_flag(uiDia, LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_add_flag(uiDia, LV_OBJ_FLAG_HIDDEN);

  uiGuia = lv_obj_create(uiPage);
  lv_obj_set_size(uiGuia, 320, 172);
  lv_obj_set_pos(uiGuia, 0, 32);
  style_clear(uiGuia);
  lv_obj_set_style_bg_opa(uiGuia, LV_OPA_TRANSP, 0);
  lv_obj_clear_flag(uiGuia, LV_OBJ_FLAG_SCROLLABLE);
  lv_obj_add_flag(uiGuia, LV_OBJ_FLAG_HIDDEN);

  uiAgent = lv_obj_create(uiPage);
  lv_obj_set_size(uiAgent, 320, 172);
  lv_obj_set_pos(uiAgent, 0, 32);
  style_clear(uiAgent);
  lv_obj_set_style_bg_opa(uiAgent, LV_OPA_TRANSP, 0);
  lv_obj_set_scroll_dir(uiAgent, LV_DIR_VER);
  lv_obj_add_flag(uiAgent, LV_OBJ_FLAG_HIDDEN);

  uiActBar = lv_obj_create(uiPage);
  lv_obj_set_size(uiActBar, 304, 34);
  lv_obj_set_pos(uiActBar, 8, 166);
  style_clear(uiActBar);
  lv_obj_set_style_bg_opa(uiActBar, LV_OPA_TRANSP, 0);
  lv_obj_set_flex_flow(uiActBar, LV_FLEX_FLOW_ROW);
  lv_obj_set_style_pad_gap(uiActBar, 12, 0);
  lv_obj_set_flex_align(uiActBar, LV_FLEX_ALIGN_SPACE_AROUND, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER);
  gold_btn(uiActBar, "aprovar", act_cb, (void*)(intptr_t)0, 90);
  gold_btn(uiActBar, "depois", act_cb, (void*)(intptr_t)1, 90);
  gold_btn(uiActBar, "recusar", act_cb, (void*)(intptr_t)2, 90);
  lv_obj_add_flag(uiActBar, LV_OBJ_FLAG_HIDDEN);

  refreshTiles();
}

static void net_timer(lv_timer_t* t) {
  (void)t;
  if (connecting && WiFi.status() == WL_CONNECTED) {
    connecting = false;
    Serial.printf("wifi %s\n", WiFi.localIP().toString().c_str());
    fetchCtrl();
    refreshTiles();
    if (page == Frota) refreshFrota();
    else if (page == Dia) refreshDia();
    else if (page == Guia) refreshGuia();
    else if (page == Agent) refreshAgent();
    else if (page != Home) fillPage(page);
  } else if (connecting && millis() - connectStarted > 18000) {
    connecting = false;
    lv_label_set_text(tileVal[0], "sem wifi");
  }
  uint32_t wait = askPending ? 1500 : 8000;
  if (!connecting && WiFi.status() == WL_CONNECTED && millis() - lastFetch > wait) {
    if (fetchCtrl()) {
      refreshTiles();
      if (page == Frota) refreshFrota();
      else if (page == Dia) refreshDia();
      else if (page == Guia) refreshGuia();
      else if (page == Agent) refreshAgent();
      else if (page != Home) fillPage(page);
    }
  }
  refreshHeader();
}

void setup() {
  Serial.begin(115200);
  pinMode(Pins::backlight, OUTPUT);
  digitalWrite(Pins::backlight, HIGH);
  pinMode(Pins::speaker, OUTPUT);
  pinMode(5, OUTPUT);
  digitalWrite(5, HIGH);
  pinMode(Pins::tftCs, OUTPUT);
  digitalWrite(Pins::tftCs, HIGH);
  pinMode(Pins::touchCs, OUTPUT);
  digitalWrite(Pins::touchCs, HIGH);
  tftSpi.begin(Pins::tftSclk, Pins::tftMiso, Pins::tftMosi, Pins::tftCs);
  tft.begin(40000000);
  tft.setRotation(1);
  tft.fillScreen(0x1082);
  touchBusBegin();
  digitalWrite(5, HIGH);
  if (loadTouchCal())
    Serial.printf("touch cal L=%d R=%d T=%d B=%d swap=%d\n", touchL, touchR, touchT, touchB, touchSwap);
  else
    Serial.printf("touch cal padrao L=%d R=%d T=%d B=%d swap=%d\n", touchL, touchR, touchT, touchB, touchSwap);

  lv_init();
  lv_disp_draw_buf_init(&drawBuf, buf1, NULL, screenW * 16);
  static lv_disp_drv_t disp_drv;
  lv_disp_drv_init(&disp_drv);
  disp_drv.hor_res = screenW;
  disp_drv.ver_res = screenH;
  disp_drv.flush_cb = flush_cb;
  disp_drv.draw_buf = &drawBuf;
  lv_disp_drv_register(&disp_drv);

  static lv_indev_drv_t indev_drv;
  lv_indev_drv_init(&indev_drv);
  indev_drv.type = LV_INDEV_TYPE_POINTER;
  indev_drv.read_cb = touch_cb;
  indev_drv.scroll_limit = 70;
  indev_drv.scroll_throw = 0;
  lv_indev_drv_register(&indev_drv);

  ui_create();
  connectWifi();
  lv_timer_create(net_timer, 400, nullptr);
  lv_timer_create(frota_anim, 180, nullptr);
  lv_timer_create(guia_anim, 160, nullptr);
  Serial.println("BOOT CONTROL lvgl tessera");
}

void loop() {
  lv_timer_handler();
  delay(5);
}
