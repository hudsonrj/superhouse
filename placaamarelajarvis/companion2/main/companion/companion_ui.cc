#include "companion_ui.h"

#include "application.h"
#include "board.h"
#include "camera.h"
#include "display.h"
#include "sensor_consent.h"

#include <esp_log.h>
#include <esp_lvgl_port.h>

#include <cstdint>
#include <cstdio>

LV_FONT_DECLARE(BUILTIN_TEXT_FONT);

namespace {

const auto kBackground = lv_color_hex(0xEFE4C4);
const auto kSurface = lv_color_hex(0xF6ECD3);
const auto kText = lv_color_hex(0x16110A);
const auto kDanger = lv_color_hex(0xC42B1C);
const auto kHeader = lv_color_hex(0x16110A);
const auto kPlate = lv_color_hex(0xF0C419);

constexpr int kHeaderHeight = 36;
constexpr int kGap = 6;

const char* TAG = "CompanionUi";

}  // namespace

CompanionUi& CompanionUi::GetInstance() {
    static CompanionUi instance;
    return instance;
}

void CompanionUi::Start() {
    if (started_) {
        return;
    }
    if (!lvgl_port_lock(3000)) {
        ESP_LOGE(TAG, "Could not lock LVGL to start companion UI");
        return;
    }

    root_ = lv_obj_create(lv_screen_active());
    lv_obj_remove_style_all(root_);
    lv_obj_set_size(root_, LV_PCT(100), LV_PCT(100));
    lv_obj_set_style_bg_color(root_, kBackground, 0);
    lv_obj_set_style_bg_opa(root_, LV_OPA_COVER, 0);
    lv_obj_set_flex_flow(root_, LV_FLEX_FLOW_COLUMN);
    lv_obj_set_style_pad_all(root_, 0, 0);
    lv_obj_clear_flag(root_, LV_OBJ_FLAG_SCROLLABLE);

    started_ = true;
    Render(Screen::kHome);
    lvgl_port_unlock();
    ESP_LOGI(TAG, "Local touch UI started");
}

void CompanionUi::RenderHeader(const char* title) {
    auto* header = lv_obj_create(root_);
    lv_obj_remove_style_all(header);
    lv_obj_set_size(header, LV_PCT(100), kHeaderHeight);
    lv_obj_set_style_bg_color(header, kHeader, 0);
    lv_obj_set_style_bg_opa(header, LV_OPA_COVER, 0);
    lv_obj_set_style_pad_hor(header, 5, 0);
    lv_obj_set_style_pad_ver(header, 3, 0);
    lv_obj_set_flex_flow(header, LV_FLEX_FLOW_ROW);
    lv_obj_set_flex_align(header, LV_FLEX_ALIGN_START, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER);
    lv_obj_clear_flag(header, LV_OBJ_FLAG_SCROLLABLE);

    if (screen_ != Screen::kHome && screen_ != Screen::kClosed) {
        auto* back = AddButton(header, "<", Action::kBack, 34, 30);
        lv_obj_set_style_bg_color(back, lv_color_hex(0x28594C), 0);
    }

    auto* label = lv_label_create(header);
    lv_label_set_text(label, title);
    lv_obj_set_flex_grow(label, 1);
    lv_obj_set_style_text_color(label, lv_color_white(), 0);
    lv_obj_set_style_text_font(label, &BUILTIN_TEXT_FONT, 0);
    lv_obj_set_style_pad_left(label, 5, 0);

    if (screen_ != Screen::kClosed) {
        auto* silent = AddButton(header, "SIL", Action::kSilent, 42, 30);
        lv_obj_set_style_bg_color(silent, lv_color_hex(0x3A3228), 0);
        lv_obj_set_style_text_color(lv_obj_get_child(silent, 0), kPlate, 0);
        auto* sos = AddButton(header, "SOS", Action::kInputCrisis, 46, 30);
        lv_obj_set_style_bg_color(sos, kDanger, 0);
        lv_obj_set_style_text_color(lv_obj_get_child(sos, 0), lv_color_white(), 0);
        auto* close = AddButton(header, "X", Action::kClose, 34, 30);
        lv_obj_set_style_bg_color(close, lv_color_hex(0x3A3228), 0);
        lv_obj_set_style_text_color(lv_obj_get_child(close, 0), kPlate, 0);
    }
}

lv_obj_t* CompanionUi::AddText(lv_obj_t* parent, const char* text, int font_size) {
    auto* label = lv_label_create(parent);
    lv_label_set_text(label, text);
    lv_label_set_long_mode(label, LV_LABEL_LONG_WRAP);
    lv_obj_set_width(label, LV_PCT(100));
    lv_obj_set_style_text_color(label, kText, 0);
    lv_obj_set_style_text_align(label, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_set_style_text_font(label, font_size >= 20 ? &BUILTIN_TEXT_FONT : &lv_font_montserrat_14, 0);
    return label;
}

lv_obj_t* CompanionUi::AddButton(lv_obj_t* parent, const char* text, Action action, int width, int height) {
    auto* button = lv_button_create(parent);
    lv_obj_set_size(button, width, height);
    lv_obj_set_style_radius(button, 6, 0);
    lv_obj_set_style_bg_color(button, kSurface, 0);
    lv_obj_set_style_bg_color(button, kPlate, LV_STATE_PRESSED);
    lv_obj_set_style_border_width(button, 2, 0);
    lv_obj_set_style_border_color(button, kText, 0);
    lv_obj_set_style_shadow_width(button, 0, 0);
    lv_obj_set_style_pad_all(button, 3, 0);
    lv_obj_add_event_cb(button, OnAction, LV_EVENT_CLICKED,
        reinterpret_cast<void*>(static_cast<intptr_t>(action)));

    auto* label = lv_label_create(button);
    lv_label_set_text(label, text);
    lv_label_set_long_mode(label, LV_LABEL_LONG_WRAP);
    lv_obj_set_width(label, LV_PCT(100));
    lv_obj_set_style_text_color(label, kText, 0);
    lv_obj_set_style_text_align(label, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_set_style_text_font(label, &lv_font_montserrat_14, 0);
    lv_obj_center(label);
    return button;
}

void CompanionUi::Render(Screen screen) {
    if (!root_) {
        return;
    }
    if (screen != screen_) {
        previous_screen_ = screen_;
    }
    screen_ = screen;
    voice_button_ = nullptr;
    lv_obj_clean(root_);

    StopToolTimer();
    const char* title = "PLACA AMARELA";
    if (screen == Screen::kEmergency) {
        title = "APOIO HUMANO";
    } else if (screen == Screen::kSensors || screen == Screen::kCameraConsent || screen == Screen::kVoiceTest) {
        title = "SENSORES LOCAIS";
    } else if (screen == Screen::kSilent) {
        title = "SILENCIO";
    } else if (screen == Screen::kBreath) {
        title = "RESPIRAR";
    } else if (screen == Screen::kGround) {
        title = "ATERRAR";
    } else if (screen == Screen::kDelay) {
        title = "ADIAR";
    } else if (screen == Screen::kToday) {
        title = "HOJE";
    } else if (screen == Screen::kStep) {
        title = "UM PASSO";
    }
    RenderHeader(title);

    body_ = lv_obj_create(root_);
    lv_obj_remove_style_all(body_);
    lv_obj_set_width(body_, LV_PCT(100));
    lv_obj_set_flex_grow(body_, 1);
    lv_obj_set_style_bg_color(body_, screen == Screen::kEmergency ? lv_color_hex(0xFFF4F2) : kBackground, 0);
    lv_obj_set_style_bg_opa(body_, LV_OPA_COVER, 0);
    lv_obj_set_style_pad_all(body_, 8, 0);
    lv_obj_set_style_pad_row(body_, kGap, 0);
    lv_obj_set_style_pad_column(body_, kGap, 0);
    lv_obj_set_flex_flow(body_, LV_FLEX_FLOW_ROW_WRAP);
    lv_obj_set_flex_align(body_, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER);
    lv_obj_clear_flag(body_, LV_OBJ_FLAG_SCROLLABLE);

    switch (screen) {
        case Screen::kHome: {
            auto* lead = AddText(body_, today_type_ == 1 ? "Uma coisa so." : "O que voce precisa agora?", 20);
            lv_obj_set_style_text_font(lead, &BUILTIN_TEXT_FONT, 0);
            auto* today = AddButton(body_, today_type_ == 1 ? "HOJE: CRISE" : today_type_ == 2 ? "HOJE: NEUTRO" : today_type_ == 3 ? "HOJE: ALTA" : "NOMEAR O DIA", Action::kToday, 276, 36);
            lv_obj_set_style_bg_color(today, today_type_ == 1 ? kDanger : kPlate, 0);
            AddButton(body_, "COMO ESTOU", Action::kStationRegulacao, 138, 40);
            AddButton(body_, "ENTENDER", Action::kStationDiagnostico, 138, 40);
            AddButton(body_, "REGULAR", Action::kBreath, 138, 40);
            AddButton(body_, "ORGANIZAR", Action::kStep, 138, 40);
            AddButton(body_, "DECISAO", Action::kDelay, 138, 40);
            AddButton(body_, "COMPANHIA", Action::kSilent, 138, 40);
            AddButton(body_, "ATERRAR", Action::kGround, 90, 34);
            AddButton(body_, "SENSORES", Action::kSensors, 90, 34);
            AddButton(body_, "SOS", Action::kInputCrisis, 90, 34);
            break;
        }
        case Screen::kToday:
            AddText(body_, "Como esta o dia ate agora?", 20);
            AddButton(body_, "CRISE", Action::kCheckCrisis, 90, 64);
            AddButton(body_, "NEUTRO", Action::kCheckNeutral, 90, 64);
            AddButton(body_, "ALTA", Action::kCheckHigh, 90, 64);
            break;
        case Screen::kStationInput:
            AddText(body_, StationName(), 20);
            AddText(body_, "Qual entrada voce consegue dar agora?", 16);
            AddButton(body_, "COMO ESTOU", Action::kInputState, 138, 54);
            AddButton(body_, "NIVEL 1 A 5", Action::kInputLevel, 138, 54);
            AddButton(body_, "PRECISO DE SOS", Action::kInputCrisis, 276, 46);
            break;
        case Screen::kSafety:
            AddText(body_, "Voce esta em um lugar fisicamente seguro?", 20);
            AddButton(body_, "SIM", Action::kSafeYes, 92, 60);
            AddButton(body_, "NAO", Action::kSafeNo, 92, 60);
            AddButton(body_, "NAO SEI", Action::kSafeUnknown, 92, 60);
            break;
        case Screen::kIntensity:
            AddText(body_, "Quanto esta dificil agora?", 20);
            AddButton(body_, "1", Action::kIntensity1, 48, 58);
            AddButton(body_, "2", Action::kIntensity2, 48, 58);
            AddButton(body_, "3", Action::kIntensity3, 48, 58);
            AddButton(body_, "4", Action::kIntensity4, 48, 58);
            AddButton(body_, "5", Action::kIntensity5, 48, 58);
            AddButton(body_, "NAO SEI", Action::kIntensityUnknown, 150, 40);
            break;
        case Screen::kAction:
            AddText(body_, CurrentActionText(), 20);
            AddButton(body_, "FIZ", Action::kActionDone, 92, 52);
            AddButton(body_, "OUTRA ACAO", Action::kActionAlternative, 92, 52);
            AddButton(body_, "PEDIR APOIO", Action::kRequestSupport, 92, 52);
            break;
        case Screen::kCheckIn:
            AddText(body_, "Agora esta...", 20);
            AddButton(body_, "MELHOR", Action::kCheckBetter, 92, 62);
            AddButton(body_, "IGUAL", Action::kCheckSame, 92, 62);
            AddButton(body_, "PIOR", Action::kCheckWorse, 92, 62);
            break;
        case Screen::kEmergency: {
            auto* text = AddText(body_, "Voce nao precisa passar por isso sozinho. Risco imediato: SAMU 192. Apoio emocional: CVV 188, 24h, gratuito.", 20);
            lv_obj_set_style_text_color(text, kDanger, 0);
            AddButton(body_, "MOSTRAR FRASE", Action::kRequestSupport, 138, 52);
            AddButton(body_, "FICAR AQUI", Action::kStay, 138, 52);
            break;
        }
        case Screen::kBreath: {
            AddText(body_, "4 entra. 6 sai. Nao force.", 16);
            auto* disc = lv_obj_create(body_);
            lv_obj_set_size(disc, 96, 96);
            lv_obj_set_style_radius(disc, LV_RADIUS_CIRCLE, 0);
            lv_obj_set_style_bg_color(disc, kPlate, 0);
            lv_obj_set_style_border_width(disc, 3, 0);
            lv_obj_set_style_border_color(disc, kText, 0);
            lv_obj_set_style_pad_all(disc, 0, 0);
            breath_label_ = lv_label_create(disc);
            lv_label_set_text(breath_label_, "INSPIRE");
            lv_obj_set_style_text_color(breath_label_, kText, 0);
            lv_obj_center(breath_label_);
            StartBreathAnimation(disc);
            AddButton(body_, "ENCERREI", Action::kExitSilent, 200, 40);
            break;
        }
        case Screen::kGround: {
            const char* senses[] = {
                "5 VEJA: cinco coisas, sem interpretar.",
                "4 TOQUE: pes, tecido, temperatura, peso.",
                "3 OUCA: longe, perto, nesta sala.",
                "2 CHEIRO: mesmo fraco, ou o ar.",
                "1 SABOR: agua, dente, nada. Corpo aqui.",
            };
            AddText(body_, senses[ground_step_ < 5 ? ground_step_ : 4], 20);
            AddButton(body_, ground_step_ >= 4 ? "ENCERRAR" : "PROXIMO SENTIDO", Action::kSenseNext, 276, 52);
            break;
        }
        case Screen::kDelay: {
            AddText(body_, "Voce nao precisa decidir agora.", 16);
            delay_left_ = 15 * 60;
            delay_label_ = AddText(body_, "15:00", 20);
            lv_obj_set_style_text_font(delay_label_, &BUILTIN_TEXT_FONT, 0);
            tool_timer_ = lv_timer_create(OnDelayTick, 1000, this);
            AddButton(body_, "CHEGA POR AGORA", Action::kExitSilent, 240, 44);
            break;
        }
        case Screen::kStep:
            AddText(body_, "Uma tarefa. Cabe em cinco minutos.", 20);
            AddButton(body_, "AGUA OU COMIDA", Action::kActionDone, 276, 40);
            AddButton(body_, "SENTAR E SOLTAR OMBROS", Action::kActionDone, 276, 40);
            AddButton(body_, "UM PAPEL COM UMA FRASE", Action::kActionDone, 276, 40);
            break;
        case Screen::kSupportPhrase:
            AddText(body_, "PRECISO DE AJUDA AGORA. POR FAVOR, FIQUE COMIGO E REDUZA OS ESTIMULOS.", 20);
            AddButton(body_, "FICAR AQUI", Action::kStay, 138, 52);
            AddButton(body_, "VOLTAR", Action::kBack, 138, 52);
            break;
        case Screen::kSilent:
            AddText(body_, "Estou aqui.", 20);
            AddButton(body_, "PRECISO DE AJUDA", Action::kSafeNo, 276, 58);
            AddButton(body_, "CONTINUAR EM SILENCIO", Action::kStay, 276, 58);
            AddButton(body_, "SAIR DO SILENCIO", Action::kExitSilent, 276, 46);
            break;
        case Screen::kSensors:
            AddText(body_, "Os testes abaixo nao enviam nem salvam audio ou imagem.", 16);
            AddButton(body_, "CAMERA", Action::kCamera, 138, 68);
            AddButton(body_, "VOZ E SOM", Action::kVoiceToggle, 138, 68);
            break;
        case Screen::kCameraConsent:
            AddText(body_, "Uma foto sera exibida somente neste aparelho e descartada depois.", 20);
            AddButton(body_, "AUTORIZAR 1 FOTO", Action::kCameraAuthorize, 276, 64);
            break;
        case Screen::kVoiceTest:
            AddText(body_, voice_recording_ ? "Gravando localmente..." : "Pronto para testar microfones e alto-falante.", 20);
            voice_button_ = AddButton(body_, voice_recording_ ? "PARAR E OUVIR" : "INICIAR GRAVACAO", Action::kVoiceToggle, 276, 68);
            break;
        case Screen::kCloseConfirm:
            AddText(body_, "Encerrar por agora?", 20);
            AddButton(body_, "ENCERRAR", Action::kCloseCycle, 138, 62);
            AddButton(body_, "CONTINUAR", Action::kBack, 138, 62);
            break;
        case Screen::kClosed:
            AddText(body_, "Ciclo encerrado por voce. Nenhuma conclusao foi presumida.", 20);
            AddButton(body_, "REABRIR", Action::kReopen, 200, 62);
            break;
    }
}

const char* CompanionUi::CurrentActionText() const {
    switch (station_) {
        case Station::kDiagnostico:
            return "Observe como hipotese: sono, energia e humor podem estar ligados. Nao conclua ainda.";
        case Station::kIdeias:
            return "Experimento pequeno: reduza uma tarefa ate ela caber em 5 minutos.";
        case Station::kAtividades:
            return intensity_ >= 4
                ? "Atividade minima: beba agua ou sente-se em um lugar menos exigente."
                : "Escolha uma atividade curta que possa terminar sem se esgotar.";
        case Station::kRegulacao:
            return "Reduza um estimulo. Apoie os pes ou sente-se, se isso for confortavel.";
        case Station::kReconhecimento:
            return "Nomeie uma coisa que voce fez apesar da dificuldade. Fato, sem elogio vazio.";
        case Station::kGatilhos:
            return "O que aconteceu imediatamente antes? Registre o fato antes da interpretacao.";
    }
    return "Faca apenas o proximo passo possivel.";
}

const char* CompanionUi::StationName() const {
    switch (station_) {
        case Station::kDiagnostico: return "ESTACAO DIAGNOSTICO";
        case Station::kIdeias: return "ESTACAO IDEIAS";
        case Station::kAtividades: return "ESTACAO ATIVIDADES";
        case Station::kRegulacao: return "ESTACAO REGULACAO";
        case Station::kReconhecimento: return "ESTACAO RECONHECIMENTO";
        case Station::kGatilhos: return "ESTACAO GATILHOS";
    }
    return "PLACA AMARELA";
}

void CompanionUi::OnAction(lv_event_t* event) {
    const auto raw = reinterpret_cast<intptr_t>(lv_event_get_user_data(event));
    GetInstance().Handle(static_cast<Action>(raw));
}

void CompanionUi::Handle(Action action) {
    switch (action) {
        case Action::kBack:
            switch (screen_) {
                case Screen::kStationInput: Render(Screen::kHome); break;
                case Screen::kSafety: Render(Screen::kStationInput); break;
                case Screen::kIntensity: Render(Screen::kSafety); break;
                case Screen::kAction: Render(Screen::kIntensity); break;
                case Screen::kCheckIn: Render(Screen::kAction); break;
                case Screen::kEmergency: Render(Screen::kSafety); break;
                case Screen::kSupportPhrase: Render(support_return_); break;
                case Screen::kSensors: Render(Screen::kHome); break;
                case Screen::kCameraConsent: Render(Screen::kSensors); break;
                case Screen::kVoiceTest:
                    if (voice_recording_) {
                        voice_recording_ = false;
                        Application::GetInstance().Schedule([]() {
                            Application::GetInstance().ToggleChatState();
                        });
                    }
                    Render(Screen::kSensors);
                    break;
                case Screen::kCloseConfirm: Render(return_screen_); break;
                case Screen::kToday:
                case Screen::kBreath:
                case Screen::kGround:
                case Screen::kDelay:
                case Screen::kStep:
                    Render(Screen::kHome);
                    break;
                default: Render(Screen::kHome); break;
            }
            return;
        case Action::kSilent:
            Render(Screen::kSilent);
            return;
        case Action::kClose:
            return_screen_ = screen_;
            Render(Screen::kCloseConfirm);
            return;
        case Action::kSensors:
            Render(Screen::kSensors);
            return;
        case Action::kStationDiagnostico: station_ = Station::kDiagnostico; Render(Screen::kStationInput); return;
        case Action::kStationIdeias: station_ = Station::kIdeias; Render(Screen::kStationInput); return;
        case Action::kStationAtividades: station_ = Station::kAtividades; Render(Screen::kStationInput); return;
        case Action::kStationRegulacao: station_ = Station::kRegulacao; Render(Screen::kStationInput); return;
        case Action::kStationReconhecimento: station_ = Station::kReconhecimento; Render(Screen::kStationInput); return;
        case Action::kStationGatilhos: station_ = Station::kGatilhos; Render(Screen::kStationInput); return;
        case Action::kInputState: Render(Screen::kSafety); return;
        case Action::kInputLevel: Render(Screen::kIntensity); return;
        case Action::kInputCrisis: Render(Screen::kEmergency); return;
        case Action::kSafeYes:
            Render(Screen::kIntensity);
            return;
        case Action::kSafeNo:
        case Action::kSafeUnknown:
            Render(Screen::kEmergency);
            return;
        case Action::kIntensity1: intensity_ = 1; Render(Screen::kAction); return;
        case Action::kIntensity2: intensity_ = 2; Render(Screen::kAction); return;
        case Action::kIntensity3: intensity_ = 3; Render(Screen::kAction); return;
        case Action::kIntensity4: intensity_ = 4; Render(Screen::kAction); return;
        case Action::kIntensity5: intensity_ = 5; Render(Screen::kAction); return;
        case Action::kIntensityUnknown: intensity_ = 0; Render(Screen::kAction); return;
        case Action::kActionDone:
            Render(Screen::kCheckIn);
            return;
        case Action::kActionAlternative:
            Render(Screen::kAction);
            return;
        case Action::kRequestSupport:
            support_return_ = screen_;
            Render(Screen::kSupportPhrase);
            return;
        case Action::kCheckBetter:
            Render(Screen::kCloseConfirm);
            return;
        case Action::kCheckSame:
            Render(Screen::kAction);
            return;
        case Action::kCheckWorse:
            if (intensity_ >= 4) {
                Render(Screen::kEmergency);
            } else {
                intensity_ = intensity_ == 0 ? 4 : intensity_ + 1;
                Render(Screen::kAction);
            }
            return;
        case Action::kStay:
            return;
        case Action::kExitSilent:
            Render(Screen::kHome);
            return;
        case Action::kToday:
            Render(Screen::kToday);
            return;
        case Action::kBreath:
            Render(Screen::kBreath);
            return;
        case Action::kGround:
            ground_step_ = 0;
            Render(Screen::kGround);
            return;
        case Action::kDelay:
            Render(Screen::kDelay);
            return;
        case Action::kStep:
            Render(Screen::kStep);
            return;
        case Action::kCheckCrisis:
            today_type_ = 1;
            station_ = Station::kRegulacao;
            Render(Screen::kBreath);
            return;
        case Action::kCheckNeutral:
            today_type_ = 2;
            Render(Screen::kHome);
            return;
        case Action::kCheckHigh:
            today_type_ = 3;
            Render(Screen::kHome);
            return;
        case Action::kSenseNext:
            if (ground_step_ >= 4) {
                Render(Screen::kHome);
            } else {
                ground_step_++;
                Render(Screen::kGround);
            }
            return;
        case Action::kCamera:
            Render(Screen::kCameraConsent);
            return;
        case Action::kCameraAuthorize:
            CaptureLocalPhoto();
            return;
        case Action::kVoiceToggle:
            if (screen_ != Screen::kVoiceTest) {
                Render(Screen::kVoiceTest);
                return;
            }
            voice_recording_ = !voice_recording_;
            Application::GetInstance().Schedule([]() {
                Application::GetInstance().ToggleChatState();
            });
            Render(Screen::kVoiceTest);
            return;
        case Action::kCloseCycle:
            if (voice_recording_) {
                Application::GetInstance().Schedule([]() {
                    Application::GetInstance().ToggleChatState();
                });
            }
            voice_recording_ = false;
            Render(Screen::kClosed);
            return;
        case Action::kReopen:
            intensity_ = 0;
            station_ = Station::kRegulacao;
            Render(Screen::kHome);
            return;
    }
}

void CompanionUi::StopToolTimer() {
    if (tool_timer_ != nullptr) {
        lv_timer_delete(tool_timer_);
        tool_timer_ = nullptr;
    }
    delay_label_ = nullptr;
    breath_label_ = nullptr;
}

void CompanionUi::StartBreathAnimation(lv_obj_t* disc) {
    lv_anim_t anim;
    lv_anim_init(&anim);
    lv_anim_set_var(&anim, disc);
    lv_anim_set_values(&anim, 78, 118);
    lv_anim_set_duration(&anim, 4000);
    lv_anim_set_reverse_duration(&anim, 6000);
    lv_anim_set_repeat_count(&anim, LV_ANIM_REPEAT_INFINITE);
    lv_anim_set_exec_cb(&anim, [](void* obj, int32_t value) {
        lv_obj_set_size(static_cast<lv_obj_t*>(obj), value, value);
    });
    lv_anim_start(&anim);
    tool_timer_ = lv_timer_create(OnBreathLabel, 200, this);
}

void CompanionUi::OnBreathLabel(lv_timer_t* timer) {
    auto* self = static_cast<CompanionUi*>(lv_timer_get_user_data(timer));
    if (self == nullptr || self->breath_label_ == nullptr) {
        return;
    }
    const uint32_t phase = lv_tick_get() % 10400;
    lv_label_set_text(self->breath_label_, phase < 4000 ? "INSPIRE" : phase < 4600 ? "SEGURE" : "SOLTE");
}

void CompanionUi::OnDelayTick(lv_timer_t* timer) {
    auto* self = static_cast<CompanionUi*>(lv_timer_get_user_data(timer));
    if (self == nullptr || self->delay_label_ == nullptr) {
        return;
    }
    if (self->delay_left_ > 0) {
        self->delay_left_--;
    }
    char buf[8];
    snprintf(buf, sizeof(buf), "%02d:%02d", self->delay_left_ / 60, self->delay_left_ % 60);
    lv_label_set_text(self->delay_label_, buf);
}

void CompanionUi::CaptureLocalPhoto() {
    SensorConsent::GetInstance().ArmCameraOnce();
    lv_obj_add_flag(root_, LV_OBJ_FLAG_HIDDEN);
    lv_timer_t* timer = lv_timer_create(RestoreAfterPreview, 5400, this);
    lv_timer_set_repeat_count(timer, 1);

    Application::GetInstance().Schedule([]() {
        auto& board = Board::GetInstance();
        auto* camera = board.GetCamera();
        const bool ok = camera != nullptr && camera->Capture();
        board.GetDisplay()->ShowNotification(ok ? "CAMERA LOCAL OK" : "FALHA NA CAMERA", 3000);
        ESP_LOGI(TAG, "Local camera test result: %s", ok ? "ok" : "failed");
    });
}

void CompanionUi::RestoreAfterPreview(lv_timer_t* timer) {
    auto* self = static_cast<CompanionUi*>(lv_timer_get_user_data(timer));
    if (self != nullptr && self->root_ != nullptr) {
        lv_obj_remove_flag(self->root_, LV_OBJ_FLAG_HIDDEN);
        self->Render(Screen::kSensors);
    }
}
