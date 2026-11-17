from . import controllers
from . import models
from . import services

def _activate_frontend_languages(env):
    """Enable supported website languages when available in this database."""
    language_codes = ['en_US', 'hi_IN', 'te_IN', 'ta_IN', 'fr_FR', 'de_DE']
    Lang = env['res.lang'].sudo()
    for code in language_codes:
        lang = Lang.search([('code', '=', code)], limit=1)
        if lang:
            lang.write({'active': True})
            continue
        activate = getattr(Lang, '_activate_lang', None)
        if activate:
            try:
                activate(code)
            except Exception:
                pass

    websites = env['website'].sudo().search([])
    active_langs = Lang.search([('code', 'in', language_codes), ('active', '=', True)])
    for website in websites:
        if hasattr(website, 'language_ids') and active_langs:
            website.write({'language_ids': [(6, 0, active_langs.ids)]})


def post_init_hook(env):
    _activate_frontend_languages(env)
    env['mouser.pricelist.generator'].generate_pricelist_items(use_live_rates=True)