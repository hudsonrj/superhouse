#ifndef COMPANION_SENSOR_CONSENT_H
#define COMPANION_SENSOR_CONSENT_H

#include <cstdint>
#include <mutex>
#include <string>

class SensorConsent {
public:
    static SensorConsent& GetInstance();

    void ArmCameraOnce(int64_t duration_ms = 60000);
    bool IsCameraArmed() const;
    bool ConsumeCameraGrant();
    void RevokeAll();
    std::string GetStatusJson() const;

private:
    SensorConsent() = default;

    bool IsCameraArmedLocked(int64_t now_us) const;

    mutable std::mutex mutex_;
    int64_t camera_expires_at_us_ = 0;
    uint8_t camera_uses_remaining_ = 0;
};

#endif
