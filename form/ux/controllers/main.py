from odoo import http
from odoo.http import request


class FeedbackController(http.Controller):

    @http.route(['/feedback'], type='http', auth='public', website=True, sitemap=True)
    def feedback_form(self, **kwargs):
        return request.render('ux.custom_feedback_page', {})

    @http.route(['/submit-feedback'], type='http', auth='public', website=True,
                methods=['POST'], csrf=True)
    def submit_feedback(self, **post):
        full_name = (post.get('fullName') or '').strip()
        email = (post.get('email') or '').strip()
        rating = post.get('rating')
        headline = (post.get('headline') or '').strip()
        feedback = (post.get('feedback') or '').strip()

        errors = []
        if not full_name:
            errors.append('Name is required.')
        if not email:
            errors.append('Email is required.')
        if not rating:
            errors.append('Rating is required.')
        if not feedback:
            errors.append('Detailed feedback is required.')

        if errors:
            # Re-render the form with the errors and the previously entered values
            # so the user doesn't have to retype everything.
            return request.render('ux.custom_feedback_page', {
                'errors': errors,
                'form_data': post,
            })

        try:
            rating_int = int(rating)
        except (TypeError, ValueError):
            rating_int = 0

        request.env['ux_form.feedback'].sudo().create({
            'name': full_name,
            'email': email,
            'rating': str(rating_int),
            'headline': headline,
            'feedback': feedback,
        })

        return request.render('ux.feedback_thank_you', {
            'full_name': full_name,
        })
