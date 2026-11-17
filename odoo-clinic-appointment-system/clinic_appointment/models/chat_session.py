from odoo import models, fields, api
import uuid


class ClinicChatSession(models.Model):
    _name = 'clinic.chat.session'
    _description = 'Chat Session Linking Doctor and Patient'
    _rec_name = 'name'
    _order = 'create_date desc'

    name = fields.Char(
        string='Session Reference',
        default='New',
        readonly=True,
    )
    session_id = fields.Char(
        string='Session ID (UUID)',
        required=True,
        readonly=True,
        default=lambda self: str(uuid.uuid4()),
    )
    appointment_id = fields.Many2one('clinic.appointment', string='Appointment')
    patient_id     = fields.Many2one('clinic.patient',     string='Patient', required=True)
    doctor_id      = fields.Many2one(
        'clinic.employee', string='Doctor',
        domain="[('role','=','doctor')]",
    )

    # Stored related fields so we can search/display without joins
    # NOTE: patient_name auto-populates from patient_id.name because store=True.
    # Do NOT pass patient_name manually in create() — Odoo resolves it from
    # the related field after patient_id is set.
    patient_name  = fields.Char(related='patient_id.name',  store=True)
    patient_phone = fields.Char(related='patient_id.phone', store=True)
    patient_email = fields.Char(related='patient_id.email', store=True)

    specialization    = fields.Char(string='Specialization Requested')
    preferred_slot    = fields.Char(string='Preferred Time Slot')
    consultation_type = fields.Selection([
        ('offline', 'Offline Consultation'),
        ('online',  'Online Consultation'),
    ], default='online')

    # ── Status flow ────────────────────────────────────────────────────
    #
    #   waiting  →  (doctor clicks Accept)  →  active  →  ended / closed
    #
    # RULES:
    #   • Every new session MUST start as 'waiting'.
    #   • A session moves to 'active' ONLY when the doctor explicitly
    #     clicks "Accept Chat" (accept_chat controller calls
    #     action_assign_doctor with activate=True).
    #   • Auto-assigning a doctor during start_chat uses activate=False
    #     so the session stays visible in the waiting queue.
    # ──────────────────────────────────────────────────────────────────
    status = fields.Selection([
        ('waiting', 'Waiting for Doctor'),
        ('active',  'Active Chat'),
        ('closed',  'Closed'),
        ('ended',   'Ended by Doctor'),
    ], default='waiting', required=True)

    create_date = fields.Datetime(string='Started At',  default=fields.Datetime.now)
    close_date  = fields.Datetime(string='Closed At')

    patient_unread = fields.Integer(string='Patient Unread', default=0)
    doctor_unread  = fields.Integer(string='Doctor Unread',  default=0)

    message_ids = fields.One2many(
        'clinic.chat.message', 'session_id',
        string='Messages',
    )

    # ── ORM overrides ─────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('clinic.chat.session')
                    or 'New'
                )
            # Safety net: ensure status always starts as 'waiting'
            if 'status' not in vals:
                vals['status'] = 'waiting'

        return super().create(vals_list)

    # ── Business logic ─────────────────────────────────────────────────

    @api.model
    def get_or_create_session(
        self,
        patient_id,
        doctor_id=None,
        appointment_id=None,
        specialization=None,
    ):
        """
        Return an existing open session for this patient, or create a new one.
        Always starts in 'waiting' state.
        """
        domain = [
            ('patient_id', '=', patient_id),
            ('status', 'in', ['waiting', 'active']),
        ]
        if doctor_id:
            domain.append(('doctor_id', '=', doctor_id))

        existing = self.search(domain, limit=1)
        if existing:
            return existing

        vals = {
            'patient_id': patient_id,
            'status': 'waiting',
        }
        if doctor_id:
            vals['doctor_id'] = doctor_id
        if appointment_id:
            vals['appointment_id'] = appointment_id
        if specialization:
            vals['specialization'] = specialization

        return self.create(vals)

    def action_assign_doctor(self, doctor_id, activate=False):
        """
        Assign a doctor to this session.

        Parameters
        ----------
        doctor_id : int | clinic.employee recordset
        activate : bool
            False (default) — session stays 'waiting'. Doctor is pre-assigned
                              but must still click Accept to go active.
            True            — session moves immediately to 'active'. Only called
                              from accept_chat controller when doctor clicks Accept.
        """
        if isinstance(doctor_id, int):
            doctor = self.env['clinic.employee'].sudo().browse(doctor_id)
        else:
            doctor = doctor_id

        if activate:
            self.write({
                'doctor_id':  doctor.id,
                'status':     'active',
                'close_date': False,
            })
            # Notify patient that doctor has joined
            self.env['clinic.chat.message'].sudo().create({
                'session_id':  self.id,
                'sender_type': 'system',
                'sender_name': 'System',
                'message':     'Dr. %s has joined the consultation' % doctor.name,
            })
        else:
            # Pre-assign only — session stays 'waiting'
            self.write({
                'doctor_id':  doctor.id,
                'status':     'waiting',
                'close_date': False,
            })

    def action_end_session(self):
        """Doctor ends the consultation."""
        self.write({
            'status':     'ended',
            'close_date': fields.Datetime.now(),
        })
        self.env['clinic.chat.message'].sudo().create({
            'session_id':  self.id,
            'sender_type': 'system',
            'sender_name': 'System',
            'message':     'Consultation ended by doctor.',
        })