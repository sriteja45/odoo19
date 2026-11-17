class RoleDetector:
    ADMIN_GROUPS = [
        'base.group_system',
        'clinic_appointment.group_clinic_receptionist',
        'clinic_appointment.group_clinic_doctor',
    ]

    def detect_from_odoo_user(self, user, env):
        if not user or user._is_public():
            return 'guest'
        for group_xml_id in self.ADMIN_GROUPS:
            try:
                if user.has_group(group_xml_id):
                    return 'admin'
            except Exception:
                continue
        return 'staff'

    def detect_from_request(self, request):
        if not request.env.user or request.env.user._is_public():
            return 'guest'
        return self.detect_from_odoo_user(request.env.user, request.env)
