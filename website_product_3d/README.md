# Website Product 3D Viewer — Odoo 19 Community

Reusable eCommerce product visualisation module for Odoo 19 Community.
Adds an interactive 3D viewer, a drag-to-spin 360° image viewer, and a
lightweight CSS/JS rotate+zoom viewer to the
product page, without replacing Odoo's standard product gallery.

Version: **19.0.1.14.0**

### Changes in 1.14.0
- **.gltf validation** now parses JSON and rejects files that reference external buffers/images (only self-contained .gltf or .glb accepted)
- **GLB / USDZ separation**: interactive web view uses GLB/GLTF as `src`; USDZ is attached as `ios-src` for native iOS AR when both are present
- Frontend boot / re-init simplified (observe once, refresh variant model only)

### Changes in 1.13.0
- Local-only model-viewer loading (CDN fallback disabled by default – module works offline after install)
- 360° frames use `data-src` + on-demand neighbour preloading (much lower initial page weight)
- Simplified variant → 3D model switching
- Legacy single-model field clearly marked **Deprecated** (kept for backward compatibility)

---

## 1. Quick start

1. Copy `website_product_3d` into your addons path and restart Odoo.
2. Enable developer mode → **Apps** → *Update Apps List* → install
   **Website Product 3D Viewer**.
3. The website-level switch **Enable Product 3D / 360 Viewer** defaults to
   **ON**, so the feature is available globally right after install.
   (You can still turn it off per website under Website → Configuration → Websites.)
4. Open any product → **3D / Animation** tab.
5. Choose one of the three approaches below.
6. Publish the product and open it on the website. A **Rotate / Zoom**,
   **3D View** and/or **360° View** button appears above the product detail block.

> Product-level switch **Enable 3D / Animation Viewer** must also be on
> (it defaults to True). If a product shows nothing, check that switch first.

---

## 2. Which approach should I use?

### Option A — Simple Rotate / Zoom (easiest, start here)

No extra assets. Uses the product's main photo.

1. In the **3D / Animation** tab, tick **Enable Simple Rotate / Zoom**.
2. Save. The **Rotate / Zoom** button appears on the website.

- Visitors drag left/right to rotate the image (CSS 3D).
- Scroll wheel or pinch to zoom (0.6× – 2.5×).
- **Reset** button restores the original view.
- Works with a single image — ideal first step before investing in 3D models
  or a multi-angle photo set.

### Option B — 360° image viewer

No 3D modelling required.

1. In the **3D / Animation** tab, tick **Enable 360° Image Viewer**.
2. Upload ordered photos in the **360° Frames** list (drag the handle to set
   rotation order). Shoot the product on a turntable, one photo every 10–15°.
3. Save. The **360° View** button appears on the website.

- Dedicated frames are preferred. If the list is empty, the module falls back
  to the product’s normal eCommerce images.
- 24 photos (15° steps) is a good balance; 36 is very smooth.
- Minimum 2 frames — below that the button hides itself automatically.
- Visitors drag with the mouse, swipe on touch, or use ← / → keys.

### Option C — real 3D model

Full orbit, zoom, and AR on supported phones.

1. In the **3D / Animation** tab, add rows to the **3D Models** list.
2. Upload a `.glb` (recommended), `.gltf` or `.usdz` file per row.
3. Tick **Default** on the model that should load first.
4. Optionally set **Camera Orbit** / **Field of View** per model.

Any combination of the three options can be enabled on the same product —
the visitor then gets the corresponding toggle buttons.

---

## 3. File formats

| Format | Use it for | Notes |
|---|---|---|
| `.glb` | Everyday use | Single self-contained binary file. Best choice. |
| `.gltf` | Existing glTF assets | Only **self-contained** glTF works; external `.bin`/texture references will not resolve. |
| `.usdz` | iOS AR | Add as a second model row. Served as `ios-src` so Quick Look on iPhone/iPad gets a native experience. |

Uploads are validated twice: the filename extension **and** the magic bytes of
the file content (`glTF` header for GLB, JSON for glTF, ZIP header for USDZ).
Renaming a `.zip` to `.glb` will be rejected.

---

## 4. File size and performance

Model size is the single biggest factor in how the page feels on mobile,
because the file downloads in the visitor's browser.

**Target: under 8 MB. Hard limit: 50 MB (configurable).**

Compress before uploading:

```bash
# Draco — best compression, tiny files
npx @gltf-transform/cli optimize input.glb output.glb --compress draco

# Meshopt — slightly larger, decodes faster on low-end phones
npx @gltf-transform/cli optimize input.glb output.glb --compress meshopt

# gltfpack alternative
gltfpack -i input.glb -o output.glb -cc
```

Typical result: 70–90% smaller with no visible quality loss. Also resize
textures to 1024×1024 or 2048×2048 — textures, not geometry, are usually what
makes a GLB huge.

The **MB** column in the 3D Models list shows the decoded size, and a warning
appears next to any file above the threshold.

### Configuring the limits

**Settings → Technical → Parameters → System Parameters**

| Parameter | Default | Meaning |
|---|---|---|
| `website_product_3d.max_model_size_mb` | `50` | Uploads above this are rejected. Set to `0` to disable the limit. |
| `website_product_3d.warn_model_size_mb` | `8` | Above this, a warning is shown in the form (upload still allowed). |

### Server-side behaviour

Models are streamed straight from the Odoo filestore via `ir.binary`, with
`ETag` and `304 Not Modified` support, so a large GLB is **not** decoded into
server memory on every request and repeat visitors re-use their browser cache.

---

## 5. Camera settings

Camera Orbit is written as `azimuth elevation distance`:

| Value | Effect |
|---|---|
| `0deg 75deg 105%` | Default. Slightly above eye level, 105% of the auto-computed distance. |
| `45deg 55deg 2.5m` | Rotated 45°, higher angle, fixed 2.5 m distance. |
| `auto auto 2m` | Let the viewer pick angles, fix the distance. |

**Field of View** (e.g. `30deg`) tightens the framing — lower values look more
like a telephoto lens and reduce perspective distortion.

Values cascade, most specific wins:

```
per-model setting  →  product setting  →  website default  →  built-in default
```

The **Reset Camera** button on the website returns to the configured orbit.

---

## 6. Variants

Open a **product variant** → **3D / Animation** tab → upload a variant model.

- When a visitor switches variant, the model is swapped live with no page reload.
- Variants without their own model fall back to the template's default model.
- Only worth doing when variants genuinely look different (colour, material).

---

## 7. Permissions

| Group | Access |
|---|---|
| Public / Portal | Read only, and only for **published** products |
| Internal users | Read |
| Sales Manager | Create / edit / delete 3D models |

The public model-serving route checks publication state and the current
website before serving anything, so draft products cannot be scraped by
guessing record IDs. The backend preview route requires a logged-in user.

---

## 8. Testing

```bash
odoo -d <database> -i website_product_3d --test-enable --stop-after-init
```

Covers extension and magic-byte validation, size limits, default-model
selection, and the controller's access control.

### Manual checklist before going live

- [ ] Chrome desktop — 3D loads, orbit and zoom work, Reset Camera works
- [ ] Safari on iPhone — AR button appears, `.usdz` opens in Quick Look
- [ ] Chrome on Android — AR via Scene Viewer
- [ ] Firefox — 3D loads (no AR; expected)
- [ ] Mobile 4G, throttled — check the progress bar and poster image
- [ ] A product with variants — switch variant, confirm the model swaps
- [ ] A product with **Simple Rotate / Zoom** enabled — drag rotates, scroll/pinch zooms, Reset works
- [ ] A product with 360° enabled — drag, swipe and arrow keys
- [ ] A product with a single image — the 360° button should stay hidden (simple anim still works)
- [ ] An unpublished product — its model URL should return 404 when logged out
- [ ] A deliberately corrupt `.glb` — the error message should appear
- [ ] A large GLB (> warn threshold) — yellow warning appears on product form and in the models list

---

## 9. Troubleshooting

| Symptom | Likely cause |
|---|---|
| No buttons on the product page | Website-level switch off, or product-level switch off |
| 360° button missing | Fewer than 2 distinct product images |
| "The 3D model could not be loaded" | Corrupt file, or a `.gltf` with external dependencies — re-export as `.glb` |
| Model loads very slowly | File too large; compress it (section 4) |
| AR button missing | Browser/device does not support it; Firefox and desktop browsers have no AR |
| Upload rejected on save | Wrong extension, mismatched content, or above the size limit |

---

## 10. Technical notes

- 3D rendering uses Google's [`<model-viewer>`](https://modelviewer.dev/)
  (BSD-3-Clause), bundled locally at
  `static/lib/model-viewer.min.js`. It is an ES module, so it is injected as a
  real `<script type="module">` tag rather than through Odoo's asset bundle.
  Local loading is preferred; CDN fallback is **disabled by default**
  (`ALLOW_CDN_FALLBACK = false`) so the module works fully offline after install.
- The website template is injected before `#product_detail_main`, leaving
  Odoo's own gallery untouched.
- Variant changes are detected via form `change` events plus a lightweight
  value watcher / setter patch on the hidden `product_id` input — no permanent
  polling timer and no duplicate click handlers.
- **Performance**: an `IntersectionObserver` initialises each product viewer
  only when it is near the viewport (200 px margin). The heavy `model-viewer`
  script itself is loaded only when the visitor actually opens the **3D View**
  panel. 360° frames use `data-src` and only the current frame + a small
  neighbourhood are preloaded on demand (instead of all images at once).
- **Dedicated 360° frames**: model `product.360.frame`. When a product has 2+
  frames with images, the website template uses them exclusively for the 360°
  viewer; otherwise it falls back to normal eCommerce product images.
- **Legacy field**: `product.template.product_3d_model` is marked deprecated.
  Prefer `product_3d_model_ids`. Fallback logic still works for old data.
