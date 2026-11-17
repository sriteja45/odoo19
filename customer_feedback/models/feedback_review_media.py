# -*- coding: utf-8 -*-
import base64
import logging
import mimetypes

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

_DEFAULT_IMAGE_MIMES = (
    'image/jpeg',
    'image/png',
    'image/webp',
    'image/gif',
)
_DEFAULT_VIDEO_MIMES = (
    'video/mp4',
    'video/webm',
    'video/quicktime',
)


class FeedbackReviewMedia(models.Model):
    _name = 'feedback.review.media'
    _description = 'Review Photo / Video'
    _order = 'sequence, id'

    review_id = fields.Many2one(
        'feedback.review', string='Review', required=True,
        ondelete='cascade', index=True,
    )
    attachment_id = fields.Many2one(
        'ir.attachment', string='Attachment', required=True,
        ondelete='cascade', index=True,
    )
    media_type = fields.Selection(
        [('image', 'Image'), ('video', 'Video')],
        string='Type', required=True, index=True,
    )
    status = fields.Selection(
        [
            ('pending', 'Pending Moderation'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='Status', default='pending', required=True, index=True,
    )
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(related='attachment_id.name', string='Filename', readonly=True)
    mimetype = fields.Char(related='attachment_id.mimetype', string='MIME Type', readonly=True)
    file_size = fields.Integer(related='attachment_id.file_size', string='Size (bytes)', readonly=True)
    company_id = fields.Many2one(
        related='review_id.company_id', store=True, index=True, readonly=True,
    )

    def get_public_url(self):
        """Return a stable public content URL for this media item."""
        self.ensure_one()
        att = self.attachment_id
        if not att:
            return ''
        if not att.access_token:
            att.sudo().generate_access_token()
        return '/web/content/%s?access_token=%s' % (att.id, att.access_token)

    def action_approve(self):
        self.write({'status': 'approved'})

    def action_reject(self):
        self.write({'status': 'rejected'})

    @api.model
    def _media_config(self):
        """Read Step-8 media limits from ir.config_parameter."""
        icp = self.env['ir.config_parameter'].sudo()
        enabled = icp.get_param('customer_feedback.media_enabled', 'True') == 'True'
        max_images = int(icp.get_param('customer_feedback.media_max_images', '5'))
        max_videos = int(icp.get_param('customer_feedback.media_max_videos', '2'))
        max_size_mb = float(icp.get_param('customer_feedback.media_max_size_mb', '10'))
        separate_moderation = (
            icp.get_param('customer_feedback.media_moderation_separate', 'False') == 'True'
        )
        return {
            'enabled': enabled,
            'max_images': max(0, max_images),
            'max_videos': max(0, max_videos),
            'max_size_bytes': int(max(0.1, max_size_mb) * 1024 * 1024),
            'separate_moderation': separate_moderation,
            'image_mimes': set(_DEFAULT_IMAGE_MIMES),
            'video_mimes': set(_DEFAULT_VIDEO_MIMES),
        }

    @api.model
    def _detect_media_type(self, mimetype, filename=''):
        cfg = self._media_config()
        mt = (mimetype or '').lower().strip()
        if not mt and filename:
            mt = (mimetypes.guess_type(filename)[0] or '').lower()
        if mt in cfg['image_mimes']:
            return 'image'
        if mt in cfg['video_mimes']:
            return 'video'
        return False

    @api.model
    def create_from_uploads(self, review, file_storage_list):
        """Create media rows + ir.attachment records from Werkzeug FileStorage list.

        Storage backend is Odoo's standard ir.attachment pipeline (filestore by
        default; S3 / object storage works transparently when configured at
        the Odoo instance level).
        """
        if not review:
            raise UserError('Review is required to attach media.')

        cfg = self._media_config()
        if not cfg['enabled']:
            raise UserError('Media uploads are disabled.')

        if not file_storage_list:
            return self.browse()

        existing = review.media_ids
        n_images = len(existing.filtered(lambda m: m.media_type == 'image'))
        n_videos = len(existing.filtered(lambda m: m.media_type == 'video'))

        moderation_enabled = self.env['ir.config_parameter'].sudo().get_param(
            'customer_feedback.moderation_enabled', default='True') == 'True'
        if cfg['separate_moderation']:
            default_status = 'pending' if moderation_enabled else 'approved'
        else:
            if review.status == 'approved':
                default_status = 'approved'
            elif review.status in ('rejected', 'hidden'):
                default_status = 'rejected'
            else:
                default_status = 'pending' if moderation_enabled else 'approved'

        created = self.browse()
        Attachment = self.env['ir.attachment'].sudo()

        for fs in file_storage_list:
            if not fs or not getattr(fs, 'filename', None):
                continue
            filename = fs.filename
            data = fs.read()
            if not data:
                continue
            if len(data) > cfg['max_size_bytes']:
                raise ValidationError(
                    'File "%s" exceeds the maximum size of %.1f MB.'
                    % (filename, cfg['max_size_bytes'] / (1024 * 1024))
                )
            mimetype = (getattr(fs, 'content_type', None) or '').lower() or (
                mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            )
            media_type = self._detect_media_type(mimetype, filename)
            if not media_type:
                raise ValidationError(
                    'File "%s" has unsupported type (%s). Allowed: JPEG, PNG, WebP, GIF, MP4, WebM, QuickTime.'
                    % (filename, mimetype)
                )
            if media_type == 'image':
                n_images += 1
                if n_images > cfg['max_images']:
                    raise ValidationError(
                        'Maximum of %d image(s) per review allowed.' % cfg['max_images']
                    )
            else:
                n_videos += 1
                if n_videos > cfg['max_videos']:
                    raise ValidationError(
                        'Maximum of %d video(s) per review allowed.' % cfg['max_videos']
                    )

            att = Attachment.create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(data),
                'res_model': 'feedback.review',
                'res_id': review.id,
                'mimetype': mimetype,
                'public': False,
            })
            att.generate_access_token()

            media = self.sudo().create({
                'review_id': review.id,
                'attachment_id': att.id,
                'media_type': media_type,
                'status': default_status,
                'sequence': (n_images + n_videos) * 10,
            })
            created |= media

        return created

    def unlink(self):
        """Also remove the underlying attachment when media row is deleted."""
        attachments = self.mapped('attachment_id')
        res = super().unlink()
        attachments.sudo().unlink()
        return res
