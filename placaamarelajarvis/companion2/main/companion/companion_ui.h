#ifndef COMPANION_UI_H
#define COMPANION_UI_H

#include <lvgl.h>

#include <string>

class CompanionUi {
public:
    static CompanionUi& GetInstance();

    void Start();

private:
    enum class Screen {
        kHome,
        kToday,
        kStationInput,
        kSafety,
        kIntensity,
        kAction,
        kCheckIn,
        kEmergency,
        kSupportPhrase,
        kSilent,
        kBreath,
        kGround,
        kDelay,
        kStep,
        kSensors,
        kCameraConsent,
        kVoiceTest,
        kCloseConfirm,
        kClosed,
    };

    enum class Station {
        kDiagnostico,
        kIdeias,
        kAtividades,
        kRegulacao,
        kReconhecimento,
        kGatilhos,
    };

    enum class Action {
        kBack,
        kSilent,
        kClose,
        kSensors,
        kStationDiagnostico,
        kStationIdeias,
        kStationAtividades,
        kStationRegulacao,
        kStationReconhecimento,
        kStationGatilhos,
        kInputState,
        kInputLevel,
        kInputCrisis,
        kSafeYes,
        kSafeNo,
        kSafeUnknown,
        kIntensity1,
        kIntensity2,
        kIntensity3,
        kIntensity4,
        kIntensity5,
        kIntensityUnknown,
        kActionDone,
        kActionAlternative,
        kRequestSupport,
        kCheckBetter,
        kCheckSame,
        kCheckWorse,
        kStay,
        kExitSilent,
        kToday,
        kBreath,
        kGround,
        kDelay,
        kStep,
        kCheckCrisis,
        kCheckNeutral,
        kCheckHigh,
        kSenseNext,
        kCamera,
        kCameraAuthorize,
        kVoiceToggle,
        kCloseCycle,
        kReopen,
    };

    CompanionUi() = default;
    CompanionUi(const CompanionUi&) = delete;
    CompanionUi& operator=(const CompanionUi&) = delete;

    static void OnAction(lv_event_t* event);
    static void RestoreAfterPreview(lv_timer_t* timer);

    void Handle(Action action);
    void Render(Screen screen);
    void RenderHeader(const char* title);
    lv_obj_t* AddButton(lv_obj_t* parent, const char* text, Action action, int width, int height);
    lv_obj_t* AddText(lv_obj_t* parent, const char* text, int font_size = 20);
    const char* CurrentActionText() const;
    const char* StationName() const;
    void CaptureLocalPhoto();
    void StartBreathAnimation(lv_obj_t* disc);
    void StopToolTimer();
    static void OnDelayTick(lv_timer_t* timer);
    static void OnBreathLabel(lv_timer_t* timer);

    lv_obj_t* root_ = nullptr;
    lv_obj_t* body_ = nullptr;
    lv_obj_t* voice_button_ = nullptr;
    Screen screen_ = Screen::kHome;
    Screen previous_screen_ = Screen::kHome;
    Screen return_screen_ = Screen::kHome;
    Screen support_return_ = Screen::kHome;
    Station station_ = Station::kRegulacao;
    int intensity_ = 0;
    int ground_step_ = 0;
    int delay_left_ = 0;
    int today_type_ = 0;
    lv_timer_t* tool_timer_ = nullptr;
    lv_obj_t* delay_label_ = nullptr;
    lv_obj_t* breath_label_ = nullptr;
    bool voice_recording_ = false;
    bool started_ = false;
};

#endif
