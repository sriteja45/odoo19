from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def _search_get_detail(self, website, order, options):
        """Scope the /shop search box to precise, product-identifying fields.

        By default Odoo also searches inside long description fields
        (description_sale / website_description / seo_keywords-style text).
        Because the bulk-imported catalog uses AI-generated marketing copy
        that repeats a lot of the same generic wording across unrelated
        products/categories, a search like "laptops" or "monitors" was
        matching that boilerplate text on almost every product instead of
        returning just the relevant category's items.

        Restricting search to name + part/manufacturer identifiers keeps
        results precise, the way a component distributor site (e.g. Mouser)
        behaves, and also makes "Shop by Brand" links (/shop?search=<brand>)
        actually match products via the Manufacturer field.
        """
        res = super()._search_get_detail(website, order, options)

        if res.get("model") == "product.template":
            noisy_fields = {"description_sale", "description", "website_description"}
            res["search_fields"] = [
                f for f in res.get("search_fields", []) if f not in noisy_fields
            ]

            precise_fields = [
                "default_code",
                "manufacturer",
                "manufacturer_part_no",
                "part_number",
            ]
            fetch_fields = res.setdefault("fetch_fields", [])
            for fname in precise_fields:
                if fname in self._fields:
                    if fname not in res["search_fields"]:
                        res["search_fields"].append(fname)
                    if fname not in fetch_fields:
                        fetch_fields.append(fname)

        return res

    part_number = fields.Char(string="Part Number")
    manufacturer = fields.Char(string="Manufacturer")
    manufacturer_part_no = fields.Char(string="Manufacturer Part Number")
    supplier_sku = fields.Char(string="Supplier SKU")
    ai_score = fields.Float(string="AI Score")
    approval_status = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], default='draft')
    seo_keywords = fields.Text(string="SEO Keywords")
    is_duplicate = fields.Boolean(string="Duplicate Product")
    vendor_name = fields.Char("Vendor")
    vendor_country = fields.Char("Vendor Country")
    country_of_origin = fields.Many2one('res.country', string='Country of Origin')
    warranty = fields.Char("Warranty")
    electronics_category = fields.Selection([
        ('electronics', 'Electronics'),
        ('semiconductors', 'Semiconductors'),
        ('mobiles', 'Mobiles'),
        ('laptops', 'Laptops'),
    ])

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        for product in products:
            if product.description_sale and not product.website_description:
                product.with_context(xevoria_skip_translation_queue=True).website_description = product.description_sale
        return products