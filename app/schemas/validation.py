import re
from typing import List, Tuple

from app.schemas.models import Action, Goal, StepGroup, Deeplink

COMMON_ACRONYMS = {
    "PC", "Wi-Fi", "WiFi", "ID", "SIM", "USB", "HDMI", "Bluetooth", "GPS", "NFC",
    "LTE", "5G", "4G", "3G", "VPN", "SSID", "IP", "DNS", "DHCP", "HTTP", "HTTPS",
    "API", "SDK", "UI", "UX", "OS", "RAM", "ROM", "CPU", "GPU", "AI", "ML",
    "QR", "OTP", "PIN", "IMEI", "ICCID", "MAC", "LAN", "WAN", "WLAN", "WWAN",
    "SMS", "MMS", "OTA", "FOTA", "USB-C", "USB-C", "OTG", "OTG", "DEX",
    "GB", "MB", "KB", "TB", "GHz", "MHz", "kHz", "V", "W", "A", "mAh",
}

SMALL_WORDS = {"on", "in", "and", "the", "a", "an", "of", "for", "to", "with", "by", "at", "from", "or", "as", "is", "it"}


def validate_description(description: str) -> List[str]:
    errors = []
    words = description.strip().split()
    
    if not description.startswith("It will"):
        errors.append("description must start with 'It will'")
    
    word_count = len(words)
    if word_count < 5 or word_count > 7:
        print(f"  WARNING: description should be 5-7 words (got {word_count}): '{description}'")
    
    return errors


def validate_title(title: str) -> List[str]:
    errors = []
    words = title.strip().split()
    
    word_count = len(words)
    if word_count < 2 or word_count > 3:
        errors.append(f"title must be 2-3 words (got {word_count})")
    
    if title != title.capitalize():
        errors.append("title must be in sentence case (first word capitalized, rest lowercase)")
    
    return errors


def validate_action_name(action_name: str) -> List[str]:
    errors = []
    
    words = action_name.split()
    normalized_words = []
    for i, word in enumerate(words):
        if word in COMMON_ACRONYMS:
            normalized_words.append(word)
        elif word.replace("-", "").replace(".", "").upper() in COMMON_ACRONYMS:
            normalized_words.append(word)
        elif word.lower() in SMALL_WORDS and i > 0:
            normalized_words.append(word.lower())
        else:
            normalized_words.append(word.title())
    
    expected = " ".join(normalized_words)
    if action_name != expected:
        errors.append("actionName must be in Title Case (acronyms like PC, Wi-Fi, USB allowed; small words like on, in, and allowed lowercase)")
    
    return errors


def validate_step_group(step_group: StepGroup, index: int) -> List[str]:
    errors = []
    prefix = f"StepGroup[{index}]"
    
    if step_group.validationDeeplink:
        vdl = step_group.validationDeeplink
        if vdl.resultType and vdl.condition and vdl.value is None:
            errors.append(f"{prefix}.validationDeeplink: value is required when resultType and condition are set")
    
    return errors


def validate_action(action: Action, index: int) -> List[str]:
    errors = []
    prefix = f"Action[{index}]"
    
    errors.extend([f"{prefix}.actionName: {e}" for e in validate_action_name(action.actionName)])
    errors.extend([f"{prefix}.description: {e}" for e in validate_description(action.description)])
    
    for i, step_group in enumerate(action.stepGroups):
        errors.extend(validate_step_group(step_group, i))
    
    return errors


def validate_goal(goal: Goal, index: int) -> List[str]:
    errors = []
    prefix = f"Goal[{index}]"
    
    errors.extend([f"{prefix}.title: {e}" for e in validate_title(goal.title)])
    
    for i, action in enumerate(goal.actions):
        errors.extend(validate_action(action, i))
    
    return errors


def validate_context_response(response) -> List[str]:
    errors = []
    
    for i, goal in enumerate(response.contexts):
        errors.extend(validate_goal(goal, i))
    
    return errors


def print_validation_errors(errors: List[str]) -> bool:
    if not errors:
        print("Validation passed!")
        return True
    
    print("Validation failed:")
    for error in errors:
        print(f"  - {error}")
    return False