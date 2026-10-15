#ifndef ESP32_CAMERA_H
#define ESP32_CAMERA_H

#include <esp_camera.h>
#include <lvgl.h>
#include <memory>

#include "camera.h"

class Esp32Camera : public Camera {
private:
    camera_fb_t* fb_ = nullptr;
    std::string explain_url_;
    std::string explain_token_;

public:
    Esp32Camera(const camera_config_t& config);
    ~Esp32Camera();

    virtual void SetExplainUrl(const std::string& url, const std::string& token);
    virtual bool Capture();
    // 翻转控制函数
    virtual bool SetHMirror(bool enabled) override;
    virtual bool SetVFlip(bool enabled) override;
    virtual std::string Explain(const std::string& question);
};

#endif // ESP32_CAMERA_H
