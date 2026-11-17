# -*- coding: utf-8 -*-
{
    'name': 'Website Product 3D Viewer',
    'version': '19.0.1.14.0',
    'category': 'Website/Website',
    'summary': 'Interactive 3D, 360° and simple rotate/zoom product viewer for Odoo eCommerce',
    'description': """
Website Product 3D Viewer
=========================

Reusable Odoo 19 custom module for interactive product visualisation.

Features:
* Multiple 3D models per product (with default selection and switcher)
* Dedicated poster image + automatic fallback to product image
* Download 3D model button
* Camera orbit & field-of-view controls
* Interactive 3D with Google model-viewer (local first, works offline)
* 360° image-sequence viewer with dedicated ordered frames (preferred)
  + fallback to existing product media + on-demand neighbour preloading
* Simple CSS/JS rotate + zoom on a single product image (no 3D model needed)
* Variant-specific 3D model override with live switching
* Website-level enable defaults to ON (feature available globally after install)
* Backend 3D preview on product form (multi-model aware)
* Lazy loading, progress bar, Reset Camera, error states
* .glb / .gltf / .usdz support (USDZ improves iOS AR)
* Strengthened .gltf validation (rejects external buffer/image URIs)
* GLB → src, USDZ → ios-src pairing for reliable iOS AR
* Magic-byte validation on upload + hardened controller
* 360° auto-hidden when fewer than 2 unique images
* Size limit + warning column + product-level large-model hint
* Legacy single-model field marked deprecated (kept for backward compatibility)

New in 1.14.0:
* .gltf validation parses JSON and rejects external resource dependencies
* Clean GLB/USDZ separation: src for web 3D, ios-src for iOS AR
* Frontend boot/re-init simplified (observe once, update model only)

New in 1.13.0:
* Robust local-only model-viewer loading (CDN fallback disabled by default)
* 360° frames use data-src + on-demand neighbour preloading (lower initial download)
* Simplified variant → 3D model switching (cleaner event handling)
* Legacy product_3d_model field clearly marked deprecated

New in 1.12.1:
* IntersectionObserver – initialise viewers only when near viewport
* model-viewer script still loads only when user opens 3D panel
* Tests for product.360.frame (create, ordering, defaults)
* README performance + dedicated frames notes

New in 1.12.0:
* Dedicated 360° Frames model + ordered One2many on the product form
* Website template prefers dedicated frames when 2+ exist
* Clearer global-by-default behaviour (website switch defaults ON)
* Updated help texts aligned with original meeting requirements

Previous (1.11):
* Simple Rotate / Zoom viewer – drag to rotate, scroll/pinch to zoom
* Improved backend help text and performance warnings
    """,
    'author': 'Dealwallet / Custom',
    'website': 'https://www.odoo.com',
    'license': 'LGPL-3',
    'depends': [
        'website_sale',
        'website',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/website_sale_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_product_3d/static/src/scss/product_3d.scss',
            'website_product_3d/static/src/js/product_3d_viewer.js',
        ],
        'web.assets_backend': [
            'website_product_3d/static/src/js/product_3d_backend_preview.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
