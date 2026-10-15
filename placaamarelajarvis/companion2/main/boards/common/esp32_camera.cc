#include "esp32_camera.h"
#include "display.h"
#include "board.h"
#if CONFIG_COMPANION_REMOTE_SERVICES
#include "system_info.h"
#include "jpg/image_to_jpeg.h"
#endif
#include "lvgl_display.h"
#include "sensor_consent.h"

#include <esp_log.h>
#include <esp_heap_caps.h>
#include <cstdlib>
#include <cstring>

#define TAG "Esp32Camera"

Esp32Camera::Esp32Camera(const camera_config_t& config) {
    // camera init
    esp_err_t err = esp_camera_init(&config); // 配置上面定义的参数
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Camera init failed with error 0x%x", err);
        return;
    }

    sensor_t *s = esp_camera_sensor_get(); // 获取摄像头型号
    if (s->id.PID == GC0308_PID) {
        s->set_hmirror(s, 0);  // 这里控制摄像头镜像 写1镜像 写0不镜像
    }
}

Esp32Camera::~Esp32Camera() {
    if (fb_) {
        esp_camera_fb_return(fb_);
        fb_ = nullptr;
    }
    esp_camera_deinit();
}

void Esp32Camera::SetExplainUrl(const std::string& url, const std::string& token) {
    explain_url_ = url;
    explain_token_ = token;
}

bool Esp32Camera::Capture() {
    if (fb_ != nullptr) {
        esp_camera_fb_return(fb_);
        fb_ = nullptr;
    }

    if (!SensorConsent::GetInstance().ConsumeCameraGrant()) {
        ESP_LOGW(TAG, "Camera capture denied: no active local consent");
        return false;
    }

    auto start_time = esp_timer_get_time();
    int frames_to_get = 2;
    // Try to get a stable frame
    for (int i = 0; i < frames_to_get; i++) {
        if (fb_ != nullptr) {
            esp_camera_fb_return(fb_);
        }
        fb_ = esp_camera_fb_get();
        if (fb_ == nullptr) {
            ESP_LOGE(TAG, "Camera capture failed");
            return false;
        }
    }
    auto end_time = esp_timer_get_time();
    ESP_LOGI(TAG, "Camera captured %d frames in %d ms", frames_to_get, int((end_time - start_time) / 1000));

    // 显示预览图片
    auto display = dynamic_cast<LvglDisplay*>(Board::GetInstance().GetDisplay());
    if (display != nullptr) {
        auto data = (uint8_t*)heap_caps_malloc(fb_->len, MALLOC_CAP_SPIRAM);
        if (data == nullptr) {
            ESP_LOGE(TAG, "Failed to allocate memory for preview image");
            esp_camera_fb_return(fb_);
            fb_ = nullptr;
            return false;
        }

        auto src = (uint16_t*)fb_->buf;
        auto dst = (uint16_t*)data;
        size_t pixel_count = fb_->len / 2;
        for (size_t i = 0; i < pixel_count; i++) {
            // 交换每个16位字内的字节
            dst[i] = __builtin_bswap16(src[i]);
        }

        auto image = std::make_unique<LvglAllocatedImage>(data, fb_->len, fb_->width, fb_->height, fb_->width * 2, LV_COLOR_FORMAT_RGB565);
        display->SetPreviewImage(std::move(image));
    }
    return true;
}

bool Esp32Camera::SetHMirror(bool enabled) {
    sensor_t *s = esp_camera_sensor_get();
    if (s == nullptr) {
        ESP_LOGE(TAG, "Failed to get camera sensor");
        return false;
    }
    
    esp_err_t err = s->set_hmirror(s, enabled);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to set horizontal mirror: %d", err);
        return false;
    }
    
    ESP_LOGI(TAG, "Camera horizontal mirror set to: %s", enabled ? "enabled" : "disabled");
    return true;
}

bool Esp32Camera::SetVFlip(bool enabled) {
    sensor_t *s = esp_camera_sensor_get();
    if (s == nullptr) {
        ESP_LOGE(TAG, "Failed to get camera sensor");
        return false;
    }
    
    esp_err_t err = s->set_vflip(s, enabled);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to set vertical flip: %d", err);
        return false;
    }
    
    ESP_LOGI(TAG, "Camera vertical flip set to: %s", enabled ? "enabled" : "disabled");
    return true;
}

/**
 * @brief 将摄像头捕获的图像发送到远程服务器进行AI分析和解释
 * 
 * 该函数将当前摄像头缓冲区中的图像编码为JPEG格式，并通过HTTP POST请求
 * 以multipart/form-data的形式发送到指定的解释服务器。服务器将根据提供的
 * 问题对图像进行AI分析并返回结果。
 * 
 * 实现特点：
 * - 使用独立线程编码JPEG，与主线程分离
 * - 采用分块传输编码(chunked transfer encoding)优化内存使用
 * - 通过队列机制实现编码线程和发送线程的数据同步
 * - 支持设备ID、客户端ID和认证令牌的HTTP头部配置
 * 
 * @param question 要向AI提出的关于图像的问题，将作为表单字段发送
 * @return std::string 服务器返回的JSON格式响应字符串
 *         成功时包含AI分析结果，失败时包含错误信息
 *         格式示例：{"success": true, "result": "分析结果"}
 *                  {"success": false, "message": "错误信息"}
 * 
 * @note 调用此函数前必须先调用SetExplainUrl()设置服务器URL
 * @note 函数会等待之前的编码线程完成后再开始新的处理
 * @warning 如果摄像头缓冲区为空或网络连接失败，将返回错误信息
 */
std::string Esp32Camera::Explain(const std::string& question) {
#if !CONFIG_COMPANION_REMOTE_SERVICES
    (void)question;
    throw std::runtime_error("Remote image analysis is disabled in local mode");
#else
    if (explain_url_.empty()) {
        throw std::runtime_error("Image explain URL or token is not set");
    }
    if (fb_ == nullptr) {
        throw std::runtime_error("No authorized camera frame is available");
    }

    std::unique_ptr<camera_fb_t, decltype(&esp_camera_fb_return)> captured_frame(
        fb_, &esp_camera_fb_return);
    fb_ = nullptr;

    // Keep the encoded image scoped to this request so failures release it.
    uint8_t* encoded_data = nullptr;
    size_t encoded_size = 0;
    if (!image_to_jpeg(captured_frame->buf, captured_frame->len,
            captured_frame->width, captured_frame->height,
            captured_frame->format, 80, &encoded_data, &encoded_size)) {
        throw std::runtime_error("Failed to encode camera frame");
    }
    std::unique_ptr<uint8_t, decltype(&std::free)> jpeg_data(
        encoded_data, &std::free);

    auto network = Board::GetInstance().GetNetwork();
    auto http = network->CreateHttp(3);
    // 构造multipart/form-data请求体
    std::string boundary = "----ESP32_CAMERA_BOUNDARY";

    // 配置HTTP客户端，使用分块传输编码
    http->SetHeader("Device-Id", SystemInfo::GetMacAddress().c_str());
    http->SetHeader("Client-Id", Board::GetInstance().GetUuid().c_str());
    if (!explain_token_.empty()) {
        http->SetHeader("Authorization", "Bearer " + explain_token_);
    }
    http->SetHeader("Content-Type", "multipart/form-data; boundary=" + boundary);
    http->SetHeader("Transfer-Encoding", "chunked");
    if (!http->Open("POST", explain_url_)) {
        ESP_LOGE(TAG, "Failed to connect to explain URL");
        throw std::runtime_error("Failed to connect to explain URL");
    }
    
    {
        // 第一块：question字段
        std::string question_field;
        question_field += "--" + boundary + "\r\n";
        question_field += "Content-Disposition: form-data; name=\"question\"\r\n";
        question_field += "\r\n";
        question_field += question + "\r\n";
        http->Write(question_field.c_str(), question_field.size());
    }
    {
        // 第二块：文件字段头部
        std::string file_header;
        file_header += "--" + boundary + "\r\n";
        file_header += "Content-Disposition: form-data; name=\"file\"; filename=\"camera.jpg\"\r\n";
        file_header += "Content-Type: image/jpeg\r\n";
        file_header += "\r\n";
        http->Write(file_header.c_str(), file_header.size());
    }

    // 第三块：JPEG数据
    http->Write(reinterpret_cast<const char*>(jpeg_data.get()), encoded_size);
    {
        // 第四块：multipart尾部
        std::string multipart_footer;
        multipart_footer += "\r\n--" + boundary + "--\r\n";
        http->Write(multipart_footer.c_str(), multipart_footer.size());
    }
    // 结束块
    http->Write("", 0);

    if (http->GetStatusCode() != 200) {
        ESP_LOGE(TAG, "Failed to upload photo, status code: %d", http->GetStatusCode());
        throw std::runtime_error("Failed to upload photo");
    }

    std::string result = http->ReadAll();
    http->Close();

    // Get remain task stack size
    size_t remain_stack_size = uxTaskGetStackHighWaterMark(nullptr);
    ESP_LOGI(TAG, "Explain image size=%dx%d, compressed size=%d, remain stack size=%d, question=%s\n%s",
        captured_frame->width, captured_frame->height, encoded_size,
        remain_stack_size, question.c_str(), result.c_str());
    return result;
#endif
}
