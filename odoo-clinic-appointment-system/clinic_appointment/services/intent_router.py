from typing import Optional

PRIORITY_KEYWORDS = {
    'book appointment': 'appointment',
    'available slot': 'appointment',
    'time slot': 'appointment',
    'doctor': 'doctor',
    'specialization': 'doctor',
    'service': 'service',
    'lab': 'lab',
    'test package': 'lab',
}

CLINIC_MODULES = {
    'appointment': ['appointment', 'book', 'slot', 'schedule', 'reschedule', 'cancel', 'token'],
    'doctor': ['doctor', 'specialization', 'consultant', 'availability'],
    'service': ['service', 'clinic timing', 'timing', 'open', 'contact', 'location'],
    'lab': ['lab', 'test', 'package', 'report', 'sample'],
    'general': ['hello', 'hi', 'help'],
}

MODULE_ACCESS = {
    'admin': list(CLINIC_MODULES.keys()),
    'staff': list(CLINIC_MODULES.keys()),
    'guest': ['appointment', 'doctor', 'service', 'lab', 'general'],
}


def detect_module(content: str) -> Optional[str]:
    content_lower = (content or '').lower()
    for keyword, module in PRIORITY_KEYWORDS.items():
        if keyword in content_lower:
            return module
    for module, keywords in CLINIC_MODULES.items():
        if any(keyword in content_lower for keyword in keywords):
            return module
    return 'general'


def detect_intent(content: str) -> Optional[str]:
    content_lower = (content or '').lower()
    intent_map = {
        'available_slots': ['slot', 'available time', 'time slot'],
        'doctor_list': ['doctor', 'available doctors'],
        'specialization_list': ['specialization', 'department'],
        'booking_help': ['book', 'appointment process', 'how to book'],
        'lab_tests': ['lab test', 'tests'],
        'timings': ['timing', 'open', 'working hours'],
        'contact': ['contact', 'phone', 'address', 'location'],
        'emergency': ['emergency', 'urgent', 'ambulance'],
    }
    for intent, keywords in intent_map.items():
        if any(kw in content_lower for kw in keywords):
            return intent
    return 'general_help'


def check_access(role: str, module: Optional[str]) -> bool:
    return module in MODULE_ACCESS.get(role, [])


def get_access_denied_message(role: str, module: Optional[str]) -> str:
    return f"Sorry, you do not have access to {module or 'this module'}."
