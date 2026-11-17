from odoo import models, api, fields
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont


class ResPartner(models.Model):
    _inherit = "res.partner"

    website_logo = fields.Image(
        string="Website Logo",
        compute="_compute_website_logo",
    )

    @api.depends("image_1920", "name")
    def _compute_website_logo(self):

        colors = [
            (13, 110, 253),    # Blue
            (25, 135, 84),     # Green
            (220, 53, 69),     # Red
            (111, 66, 193),    # Purple
            (253, 126, 20),    # Orange
            (32, 201, 151),    # Teal
            (232, 62, 140),    # Pink
            (102, 16, 242),    # Indigo
            (13, 202, 240),    # Cyan
            (255, 193, 7),     # Yellow
            (108, 117, 125),   # Gray
            (0, 123, 255),     # Primary Blue
        ]

        for rec in self:

            # Use uploaded logo if available
            if rec.image_1920:
                rec.website_logo = rec.image_1920
                continue

            company_name = (rec.name or "Vendor").strip()
            words = [w for w in company_name.split() if w]

            # Generate 2-letter logo text
            if len(words) >= 2:
                logo_text = (
                    words[0][0] +
                    words[1][0]
                ).upper()
            else:
                logo_text = company_name[:2].upper()

            color = colors[
                abs(hash(company_name)) % len(colors)
            ]

            width = 420
            height = 220

            img = Image.new(
                "RGBA",
                (width, height),
                (255, 255, 255, 0)
            )

            draw = ImageDraw.Draw(img)

            # Rounded rectangle background
            draw.rounded_rectangle(
                (0, 0, width - 1, height - 1),
                radius=40,
                fill=color
            )

            try:
                font = ImageFont.truetype(
                    "DejaVuSans-Bold.ttf",
                    95
                )
            except Exception:
                font = ImageFont.load_default()

            bbox = draw.textbbox(
                (0, 0),
                logo_text,
                font=font
            )

            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            x = (width - text_width) / 2
            y = (height - text_height) / 2

            draw.text(
                (x, y),
                logo_text,
                fill="white",
                font=font
            )

            buffer = BytesIO()
            img.save(buffer, format="PNG")

            rec.website_logo = base64.b64encode(
                buffer.getvalue()
            )
