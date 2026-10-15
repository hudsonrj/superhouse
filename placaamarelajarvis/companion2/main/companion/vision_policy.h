#ifndef COMPANION_VISION_POLICY_H
#define COMPANION_VISION_POLICY_H

#include <string>

enum class VisionPurpose {
    kScene,
    kWellbeingCheckIn,
    kMedicationLabel,
};

VisionPurpose ParseVisionPurpose(const std::string& value);
std::string BuildSafeVisionQuestion(
    VisionPurpose purpose,
    const std::string& user_question);

#endif
