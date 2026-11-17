from odoo import http, fields
from odoo.http import request
from datetime import datetime,date

class ClinicWebsiteBooking(http.Controller):

    # ================= HOME PAGE =================
    @http.route('/clinic', type='http', auth='public', website=True)
    def homepage(self):
        return request.render('clinic_appointment.clinic_homepage')

    
    # ================= BOOKING FORM =================
    @http.route('/clinic/book', type='http', auth='public', website=True)
    def booking_form(self, doctor_id=None, appointment_date=None, **kwargs):
        
        doctors = request.env['clinic.employee'].sudo().search([
            ('active', '=', True),
            ('role', '=', 'doctor')
        ])
        specializations = request.env['clinic.specialization'].sudo().search([])

        return request.render('clinic_appointment.booking_form_template', {
            'doctors': doctors,
            'specializations': specializations,
            'selected_doctor': int(doctor_id) if doctor_id else False,
            'selected_date': appointment_date,
        })
    
    # ================= GET AVAILABLE SLOTS =================
    @http.route('/get_slots', type='json', auth='public', website=True)
    def get_slots(self, doctor_id, date):

        if not doctor_id or not date:
            return []

        doctor = request.env['clinic.employee'].sudo().browse(int(doctor_id))

        if not doctor.exists():
            return []

        # Generate slots first
        request.env['clinic.appointment.slot'].sudo().generate_slots(doctor, date)

        # Fetch only available slots
        slots = request.env['clinic.appointment.slot'].sudo().search([
            ('doctor_id', '=', doctor.id),
            ('slot_date', '=', date),
            ('is_booked', '=', False)
        ], order='start_time asc')

        return [
            {
                'id': slot.id,
                'name': slot.name
            }
            for slot in slots
        ]


    # ================= SUBMIT BOOKING =================
    @http.route('/clinic/submit', type='http', auth='public', methods=['POST'], website=True, csrf=True)
    def booking_submit(self, **post):

        print("FORM DATA:", post)

        doctor_id = int(post.get('doctor_id') or 0)
        spec_id = int(post.get('specialization_id') or 0)
        slot_id = int(post.get('slot_id') or 0)

        appointment_vals = {
            'appointment_id': 'New',
            'patient_name': (post.get('patient_name') or '').strip(),
            'birth_date': post.get('birth_date') or False,
            'gender': post.get('gender') or False,
            'email': (post.get('email') or '').strip(),
            'phone': (post.get('phone_full') or post.get('phone') or '').strip(),
            'specialization_id': spec_id if spec_id else False,
            'doctor_id': doctor_id,
            'appointment_date': post.get('appointment_date') or False,
            'slot_id': slot_id,
            'booking_by': 'customer',
            'reason': post.get('reason') or False,
            'other_reason': post.get('other_reason') or False,
        }

        print("VALUES:", appointment_vals)

        # 🔥 NO TRY BLOCK
        appointment = request.env['clinic.appointment'].sudo().create(appointment_vals)

        return request.render(
            'clinic_appointment.booking_thank_you_template',
            {'appointment': appointment}
        )

    # ================= DOCTORS PAGE =================
    @http.route('/clinic/doctors', type='http', auth='public', website=True)
    def doctors_page(self):
        doctors = request.env['clinic.employee'].sudo().search([('role', '=', 'doctor'), ('active', '=', True)])
        return request.render('clinic_appointment.clinic_doctors_page', {'doctors': doctors})

    @http.route('/clinic/doctor/<int:doctor_id>', type='http', auth='public', website=True)
    def doctor_detail(self, doctor_id):
        doctor = request.env['clinic.employee'].sudo().browse(doctor_id)
        return request.render('clinic_appointment.clinic_doctor_detail', {'doctor': doctor})

    # ================= SERVICES PAGE =================
    @http.route('/clinic/services', type='http', auth='public', website=True)
    def services(self):
        return request.render('clinic_appointment.clinic_services_page')

    # ================= ABOUT PAGE =================
    @http.route('/clinic/about', type='http', auth='public', website=True)
    def about(self):
        return request.render('clinic_appointment.clinic_about_page')

    # ================= CONTACT PAGE =================
    @http.route('/clinic/contact', type='http', auth='public', website=True)
    def contact(self):
        return request.render('clinic_appointment.clinic_contact_page')
    
    # ================= SUBMIT ENQUIRY =================
    @http.route('/clinic/submit_enquiry', type='http', auth='public', website=True, csrf=True)
    def submit_enquiry(self, **post):

        request.env['clinic.enquiry'].sudo().create({
            'name': post.get('name'),
            'email': post.get('email'),
            'phone': post.get('phone'),
            'department_id': int(post.get('department_id')) if post.get('department_id') else False,
            'message': post.get('message'),
        })

        return request.redirect('/clinic/contact?success=1')
    
    
    @http.route('/clinic/lab-tests', type='http', auth='public', website=True)
    def lab_tests_page(self):
        return request.render('clinic_appointment.lab_tests_and_packages_page')
    
    @http.route('/clinic/dashboard', type='json', auth='user')
    def dashboard_data(self):
        return request.env['clinic.dashboard'].sudo().get_dashboard_data()