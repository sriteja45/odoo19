# Run inside: odoo-bin shell -d STAGING_DB
# Usage: exec(open('path/to/run_audit.py').read())

def feedback_audit(env):
    Review = env['feedback.review']
    Rating = env['rating.rating']
    approved = Review.search([('status', '=', 'approved')])
    linked = approved.filtered('rating_id')
    orphans = approved - linked
    consumed = Rating.search([
        ('res_model', '=', 'product.template'),
        ('consumed', '=', True),
    ])
    foreign_consumed = Rating.search([
        ('res_model', '=', 'product.template'),
        ('consumed', '=', True),
        '|',
        ('feedback_review_id', '=', False),
        ('feedback_review_id.status', '!=', 'approved'),
    ])
    mismatches = []
    for tmpl in env['product.template'].search([('rating_count', '>', 0)]):
        stats = Review._assert_native_matches_approved(tmpl)
        if not stats['match']:
            mismatches.append({'product': tmpl.display_name, **stats})
    return {
        'review_total': Review.search_count([]),
        'approved': len(approved),
        'linked': len(linked),
        'orphans_approved_unbridged': len(orphans),
        'native_consumed_product': len(consumed),
        'foreign_consumed_product': len(foreign_consumed),
        'mismatches': mismatches,
    }

print(feedback_audit(env))
