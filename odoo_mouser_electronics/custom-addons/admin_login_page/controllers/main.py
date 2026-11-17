from odoo import http
from odoo.http import request


class CustomSignupController(http.Controller):

    @http.route('/custom/signup',
                type='http',
                auth='public',
                website=True)
    def custom_signup(self, **kw):

        return request.render(
            'admin_login_page.custom_signup_template'
        )

    @http.route('/custom/signup/submit',
                type='http',
                auth='public',
                website=True,
                csrf=False)
    def custom_signup_submit(self, **post):

        name = post.get('name')
        email = post.get('email')
        password = post.get('password')

        existing_user = request.env['res.users'].sudo().search(
            [('login', '=', email)],
            limit=1
        )

        if existing_user:
            return request.render(
                'admin_login_page.custom_signup_template',
                {
                    'error': 'Email already exists'
                }
            )

        request.env['res.users'].sudo().create({
            'name': name,
            'login': email,
            'email': email,
            'password': password,
        })

        return request.redirect('/web/login')