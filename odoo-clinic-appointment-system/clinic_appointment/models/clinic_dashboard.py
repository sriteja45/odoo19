# models/dashboard.py

from odoo import models, api
from datetime import date

class ClinicDashboard(models.AbstractModel):
    _name = 'clinic.dashboard'
    _description = 'Clinic Dashboard'

    