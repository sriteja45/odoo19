import re
from agno.tools import Toolkit


def build_toolkit(env, is_admin: bool, agent_ref=None) -> Toolkit:
    def _cache(result: str) -> str:
        if agent_ref is not None:
            agent_ref._last_tool_result = result
        return result

    def _find_doctor(name: str):
        return env['clinic.employee'].sudo().search([
            ('role', '=', 'doctor'),
            ('name', 'ilike', name),
            ('active', '=', True),
        ], limit=1)

    def get_doctors (null) -> str:
        doctors = env['clinic.employee'].sudo().search([
            ('role', '=', 'doctor'),
            ('active', '=', True),
        ], order='name asc', limit=20)
        if not doctors:
            return _cache('👨‍⚕️ Doctors\n----------------------\nNo active doctors found.')
        lines = ['👨‍⚕️ Doctors', '----------------------', f'Total Found    : {len(doctors)}', '']
        for idx, d in enumerate(doctors, 1):
            fee = f"{d.consultation_fee:.2f}" if d.consultation_fee else 'N/A'
            lines += [
                f'{idx}. {d.name}',
                f'   - Specialization : {d.display_specialization or d.specialization_id.name or "N/A"}',
                f'   - Available      : {d.available_from or "N/A"} to {d.available_to or "N/A"}',
                f'   - Fee            : {fee}',
            ]
        return _cache('\n'.join(lines))

    def get_specializations() -> str:
        specs = env['clinic.specialization'].sudo().search([], order='name asc')
        if not specs:
            return _cache('📝 Specializations\n----------------------\nNo specializations found.')
        lines = ['📝 Specializations', '----------------------', f'Total Found    : {len(specs)}', '']
        for idx, s in enumerate(specs, 1):
            lines.append(f'{idx}. {s.name}')
        return _cache('\n'.join(lines))

    def get_available_slots(doctor_name: str, appointment_date: str) -> str:
        if not doctor_name or not appointment_date:
            return _cache('📅 Available Slots\n----------------------\nPlease provide doctor name and appointment date in YYYY-MM-DD format.')
        doctor = _find_doctor(doctor_name)
        if not doctor:
            return _cache(f"📅 Available Slots\n----------------------\nDoctor '{doctor_name}' not found.")
        env['clinic.appointment.slot'].sudo().generate_slots(doctor, appointment_date)
        slots = env['clinic.appointment.slot'].sudo().search([
            ('doctor_id', '=', doctor.id),
            ('slot_date', '=', appointment_date),
            ('is_booked', '=', False),
        ], order='start_time asc')
        if not slots:
            return _cache(f'📅 Available Slots\n----------------------\nNo free slots available for {doctor.name} on {appointment_date}.')
        lines = [f'📅 Available Slots — {doctor.name}', '----------------------', f'Date           : {appointment_date}', f'Total Found    : {len(slots)}', '']
        for idx, slot in enumerate(slots, 1):
            lines.append(f'{idx}. {slot.name}')
        return _cache('\n'.join(lines))

    def get_booking_help() -> str:
        return _cache(
            '📝 Appointment Booking Help\n'
            '----------------------\n'
            '1. Open /clinic/book\n'
            '2. Select specialization\n'
            '3. Select doctor\n'
            '4. Select appointment date\n'
            '5. Choose available slot\n'
            '6. Enter patient details\n'
            '7. Submit the form\n'
            '8. Your appointment will be created successfully.'
        )

    def get_lab_tests(limit: int = 10) -> str:
        tests = env['clinic.lab.test'].sudo().search([('is_template', '=', True)], order='name asc', limit=limit)
        if not tests:
            return _cache('🧪 Lab Tests\n----------------------\nNo lab test templates found.')
        lines = ['🧪 Lab Tests', '----------------------', f'Total Found    : {len(tests)}', '']
        for idx, t in enumerate(tests, 1):
            lines += [
                f'{idx}. {t.name}',
                f'   - Category   : {t.category or "N/A"}',
                f'   - Price      : {t.price:.2f} {t.currency_id.name if t.currency_id else ""}',
            ]
        return _cache('\n'.join(lines))

    

    def get_contact_info() -> str:
        return _cache(
            '📞 Contact Information\n'
            '----------------------\n'
            'Phone          : +91-9876543210\n'
            'Location       : Main Road, Hyderabad\n'
            'Page           : /clinic/contact'
        )

    def get_clinic_timings() -> str:
        return _cache(
            '⏰ Clinic Timings\n'
            '----------------------\n'
            'Monday to Saturday : 9:00 AM to 8:00 PM\n'
            'Sunday             : Closed'
        )

    def get_emergency_help() -> str:
        return _cache(
            '⚠️ Emergency Help\n'
            '----------------------\n'
            'For emergency assistance, please call 108 immediately.'
        )

    toolkit = Toolkit(name='clinic_toolkit')
    for func in [
        get_doctors,
        get_specializations,
        get_available_slots,
        get_booking_help,
        get_lab_tests,
        get_contact_info,
        get_clinic_timings,
        get_emergency_help,
    ]:
        toolkit.register(func)
    return toolkit
