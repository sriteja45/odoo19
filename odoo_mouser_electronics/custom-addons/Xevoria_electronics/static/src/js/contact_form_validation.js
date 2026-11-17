/* Xevoria: Contact Us form validation
 * - Name field: only letters, spaces, apostrophes and hyphens allowed (no digits).
 * - Phone Number field: only digits, spaces, +, -, ( ) allowed (no letters).
 */
(function () {
    "use strict";

    function findFields(form) {
        var nameField = form.querySelector(
            'input[name="name"], input[name="contact_name"]'
        );
        var phoneField = form.querySelector(
            'input[name="phone"], input[name="contact_phone"], input[type="tel"]'
        );
        var companyField = form.querySelector(
            'input[name="company"], input[name="contact_company"]'
        );
        return { nameField: nameField, phoneField: phoneField, companyField: companyField };
    }

    // Keeps only letters (incl. accented), spaces, apostrophes and hyphens.
    function sanitizeName(value) {
        return value.replace(/[^A-Za-zÀ-ÖØ-öø-ÿ' -]/g, "");
    }

    // Keeps only digits, spaces, +, -, ( ) which are valid phone number characters.
    function sanitizePhone(value) {
        return value.replace(/[^0-9+\-() ]/g, "");
    }

    // Company name: letters, spaces and common punctuation (& . , - ') allowed, no digits.
    function sanitizeCompany(value) {
        return value.replace(/[^A-Za-zÀ-ÖØ-öø-ÿ&.,' -]/g, "");
    }

    function attachRealtimeFilter(field, sanitizer) {
        if (!field || field.dataset.validationAttached) {
            return;
        }
        field.dataset.validationAttached = "1";
        field.addEventListener("input", function () {
            var cursor = field.selectionStart;
            var before = field.value;
            var after = sanitizer(before);
            if (after !== before) {
                field.value = after;
                var diff = before.length - after.length;
                if (cursor !== null) {
                    field.selectionStart = field.selectionEnd = Math.max(
                        0,
                        cursor - diff
                    );
                }
            }
        });
    }

    function showFieldError(field, message) {
        clearFieldError(field);
        var error = document.createElement("div");
        error.className = "text-danger o_contact_validation_error small mt-1";
        error.textContent = message;
        field.insertAdjacentElement("afterend", error);
        field.classList.add("is-invalid");
    }

    function clearFieldError(field) {
        field.classList.remove("is-invalid");
        var next = field.nextElementSibling;
        if (next && next.classList.contains("o_contact_validation_error")) {
            next.remove();
        }
    }

    function isValidName(value) {
        return /^[A-Za-zÀ-ÖØ-öø-ÿ' -]+$/.test(value.trim());
    }

    function isValidPhone(value) {
        if (!value.trim()) {
            return true; // Phone Number is optional on the default contact form.
        }
        return /^[0-9+\-() ]+$/.test(value) && /\d/.test(value);
    }

    function isValidCompany(value) {
        if (!value.trim()) {
            return true; // Company is optional on the default contact form.
        }
        return /^[A-Za-zÀ-ÖØ-öø-ÿ&.,' -]+$/.test(value.trim());
    }

    function attachSubmitValidation(form, nameField, phoneField, companyField) {
        if (form.dataset.validationSubmitAttached) {
            return;
        }
        form.dataset.validationSubmitAttached = "1";
        form.addEventListener(
            "submit",
            function (ev) {
                var hasError = false;

                if (nameField) {
                    if (!isValidName(nameField.value)) {
                        showFieldError(
                            nameField,
                            "Name should not contain numbers."
                        );
                        hasError = true;
                    } else {
                        clearFieldError(nameField);
                    }
                }

                if (phoneField) {
                    if (!isValidPhone(phoneField.value)) {
                        showFieldError(
                            phoneField,
                            "Phone Number should contain digits only."
                        );
                        hasError = true;
                    } else {
                        clearFieldError(phoneField);
                    }
                }

                if (companyField) {
                    if (!isValidCompany(companyField.value)) {
                        showFieldError(
                            companyField,
                            "Company name should not contain numbers."
                        );
                        hasError = true;
                    } else {
                        clearFieldError(companyField);
                    }
                }

                if (hasError) {
                    ev.preventDefault();
                    ev.stopPropagation();
                }
            },
            true
        );
    }

    function initContactFormValidation() {
        var forms = document.querySelectorAll(
            "form.s_website_form, #contactus_form, form[data-model_name]"
        );
        forms.forEach(function (form) {
            var fields = findFields(form);
            if (!fields.nameField && !fields.phoneField && !fields.companyField) {
                return;
            }
            attachRealtimeFilter(fields.nameField, sanitizeName);
            attachRealtimeFilter(fields.phoneField, sanitizePhone);
            attachRealtimeFilter(fields.companyField, sanitizeCompany);
            attachSubmitValidation(form, fields.nameField, fields.phoneField, fields.companyField);
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initContactFormValidation);
    } else {
        initContactFormValidation();
    }

    // The website editor can inject the form asynchronously; re-check shortly after load.
    window.addEventListener("load", function () {
        setTimeout(initContactFormValidation, 500);
    });
})();
