#include "sensor_consent.h"

#include <esp_timer.h>

SensorConsent& SensorConsent::GetInstance() {
    static SensorConsent instance;
    return instance;
}

void SensorConsent::ArmCameraOnce(int64_t duration_ms) {
    std::lock_guard<std::mutex> lock(mutex_);
    camera_expires_at_us_ = esp_timer_get_time() + (duration_ms * 1000);
    camera_uses_remaining_ = 1;
}

bool SensorConsent::IsCameraArmedLocked(int64_t now_us) const {
    return camera_uses_remaining_ > 0 && now_us <= camera_expires_at_us_;
}

bool SensorConsent::IsCameraArmed() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return IsCameraArmedLocked(esp_timer_get_time());
}

bool SensorConsent::ConsumeCameraGrant() {
    std::lock_guard<std::mutex> lock(mutex_);
    if (!IsCameraArmedLocked(esp_timer_get_time())) {
        camera_expires_at_us_ = 0;
        camera_uses_remaining_ = 0;
        return false;
    }

    --camera_uses_remaining_;
    if (camera_uses_remaining_ == 0) {
        camera_expires_at_us_ = 0;
    }
    return true;
}

void SensorConsent::RevokeAll() {
    std::lock_guard<std::mutex> lock(mutex_);
    camera_expires_at_us_ = 0;
    camera_uses_remaining_ = 0;
}

std::string SensorConsent::GetStatusJson() const {
    const bool camera_armed = IsCameraArmed();
    return std::string("{\"camera_armed\":") +
        (camera_armed ? "true" : "false") +
        ",\"camera_grant\":\"single_capture_60s\"" +
        ",\"microphone_mode\":\"button_started_session\"" +
        ",\"media_storage\":\"disabled\"}";
}
