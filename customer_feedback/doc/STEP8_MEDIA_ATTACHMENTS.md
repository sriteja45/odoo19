# Step 8 — Review Photos & Videos

## Goal
Allow verified customers to attach photos and short videos to a review, store them via Odoo's standard `ir.attachment` pipeline (local filestore or S3/object storage when the instance is configured for it), provide a simple upload widget on the public review form, and gate public visibility through moderation.

## Storage
- Binary files are stored as `ir.attachment` linked to `feedback.review` (`res_model` / `res_id`).
- A thin business model `feedback.review.media` holds type (image/video), sequence, and moderation status, and points at the attachment.
- No custom S3 client is required: when Odoo is configured with object storage for attachments, uploads go there automatically.

## Upload widget (portal)
- Multipart form on `/feedback/review/<token>/submit`.
- Multi-file input (`media_files`) accepting JPEG, PNG, WebP, GIF, MP4, WebM, QuickTime.
- Limits (configurable under **Settings → Customer Feedback → Review Photos & Videos**):
  - Enable/disable media
  - Max images / max videos per review
  - Max file size (MB)
  - Separate media moderation (optional)

## Moderation gate
- **Default (separate media moderation off):** media status follows the parent review (`pending` → `approved` / `rejected` together).
- **Separate media moderation on:** each media row has its own status; moderators can approve/reject individual items from the review form.
- Public product page and portal only render media with `status == approved` via `feedback.review.get_public_media()`.

## Backend
- Review form: list of media with Approve/Reject buttons.
- List view: optional `media_count` column.
- Access rights aligned with existing feedback manager/moderator/user/portal/public groups.

## Public display
- Product-page review cards show image thumbnails (linked) and inline video players for approved media only.

## Security notes
- Uploads only accepted on the token-secured submit route (CSRF + rate limit already applied).
- MIME/type and size validated server-side before creating attachments.
- Attachments are not public by default; product-page URLs use `access_token`.
