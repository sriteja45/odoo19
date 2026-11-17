## Product Image Retrieval Verification

### Overview

Verified that product images stored in Odoo can be accessed using the standard `/web/image` endpoint. Product images are stored as attachments (`ir_attachment`) and linked to the corresponding `product.template` record.

### Steps Performed

#### 1. Identify Product ID

The product image URL requires the Product Template ID (`product.template.id`).

Example:

```sql
SELECT
    id,
    default_code,
    name
FROM product_template
WHERE default_code = 'SAMSUNG_MOBILE';
```

Sample Result:

```text
id: 123
default_code: SAMSUNG_MOBILE
name: Samsung Mobile
```

---

#### 2. Verify Image Attachment

Checked the `ir_attachment` table for image records associated with the product.

```sql
SELECT
    id,
    res_model,
    res_id,
    res_field,
    mimetype,
    file_size
FROM ir_attachment
WHERE res_model = 'product.template'
AND res_field = 'image_1920';
```

Expected Result:

```text
res_model : product.template
res_id    : 123
res_field : image_1920
mimetype  : image/jpeg
```

This confirms that the image is attached to the product.

---

#### 3. Construct Image URL

Generated the image URL using the standard Odoo image route:

```text
https://mouserelectronics.dealwallet.com/web/image/product.template/123/image_1920
```

Format:

```text
<ODOO_BASE_URL>/web/image/product.template/<PRODUCT_ID>/image_1920
Here, PRODUCT_ID is res_id in table ir_attachment
```

Examples:

```text
https://mouserelectronics.dealwallet.com/web/image/product.template/123/image_1920
https://mouserelectronics.dealwallet.com/web/image/product.template/456/image_1920
```

---

#### 4. Verify Using Postman

Opened Postman and sent a GET request:

```http
GET http://localhost:8069/web/image/product.template/123/image_1920
```

Result:

* Image successfully returned.
* Response content type: `image/jpeg`.
* Product image rendered correctly in Postman.

---

### Alternative Image Sizes

Odoo automatically generates multiple image resolutions:

```text
image_1920
image_1024
image_512
image_256
image_128
```

Examples:

```text
/web/image/product.template/123/image_1024
/web/image/product.template/123/image_512
/web/image/product.template/123/image_256
```

These can be used for website, mobile applications, and APIs to reduce payload size.

---


This can be used in custom APIs (FastAPI, Odoo Controllers, JSON-2 API) to expose product image URLs.

### Outcome

* Successfully identified product images through `product.template` records.
* Verified image storage in `ir_attachment`.
* Generated image URLs using Odoo's standard `/web/image` endpoint.
* Successfully tested image retrieval through Postman.
* Confirmed that image URLs can be exposed through custom APIs for website, mobile, and POS integrations.
