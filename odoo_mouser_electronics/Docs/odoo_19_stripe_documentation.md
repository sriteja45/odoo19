# Stripe Payment Provider Integration — Odoo 19.0 Documentation

[Stripe](https://stripe.com) is a popular and robust online payment processing platform that integrates seamlessly with Odoo. It allows businesses to accept credit cards, debit cards, and a variety of regional electronic payment methods directly through their Odoo website, e-commerce platform, or invoicing portals.

## Prerequisites & Resources
Before beginning your integration, please verify regional capabilities and support features using the official resources:
* **Global Availability:** Check the [List of countries supported by Stripe](https://stripe.com/global).
* **Payment Types:** See the [List of payment methods supported by Stripe](https://stripe.com/payments/payment-methods).
* **Odoo Point of Sale Integration:** For brick-and-mortar stores, learn how to [Use Stripe as a payment terminal in Point of Sale](../../sales/point_of_sale/payment_methods/terminals/stripe.html).

---

## Create or Connect Your Stripe Account with Odoo

To establish a connection between a new Stripe account and your Odoo 19.0 database, verify that your company's email address is correctly configured within the **Company Settings**. Follow the appropriate instructions based on your deployment ecosystem:

### For Odoo Online (SaaS) Users
1. Navigate to the **Payment Providers** dashboard in Odoo and select **Stripe**.
2. Click the **Connect Stripe** button.
3. Complete the on-screen configuration and onboarding wizard provided by Stripe.
4. Confirm your email address using the activation/verification message sent directly by Stripe.
5. Once finalized, click **Agree and submit** at the end of the onboarding flow. You will be automatically redirected back to your Odoo database, and your provider status will switch to **Enabled**.

### For Odoo.sh or On-Premise Deployments
1. Navigate to the **Payment Providers** dashboard in Odoo and locate **Stripe**.
2. Click **Connect Stripe**.
3. Proceed through the configuration process, confirming your registration email address when prompted by Stripe.
4. After completing the Stripe wizard, click **Agree and submit**. This will route you back to the **Stripe Payment Provider** form view in Odoo.
5. Manually [fill in your specific credentials](#manual-credential-input) to finish linking.
6. Toggle or update the **State** field to **Enabled**.

> 💡 **Tip:** If you mistakenly created a brand new account instead of linking an existing configuration, activate **Developer Mode** in Odoo, click **Reset your Stripe Account** on the Stripe payment provider configuration form, and manually fill in the correct credentials.

---

## Manual Credential Input

Manual configuration is mandatory under certain circumstances, including when connecting an existing standalone Stripe account to Odoo, configuring on-premise/Odoo.sh environments, or setting up non-live test testing suites.

### Step 1: Stripe Dashboard Configuration
1. Log into your account via the [Stripe Dashboard](https://dashboard.stripe.com/).
2. Navigate to **Developers** ‣ **API Keys** (or go straight to the [API Keys dashboard page](https://dashboard.stripe.com/account/apikeys)).
3. Under the **Standard keys** table, retrieve and copy both the **Publishable key** and the **Secret key**. Save these strings securely for the next step.

### Step 2: Odoo Dashboard Configuration
1. Activate **Developer Mode** within your Odoo instance.
2. Navigate to **Accounting** (or **Invoicing**) ‣ **Configuration** ‣ **Payment Providers** and select **Stripe**.
3. Access the **Credentials** tab on the form view.
4. Paste the respective strings into the **Publishable Key** and **Secret Key** fields that you collected from your Stripe Dashboard.
5. Click the **Generate your webhook** button to automate webhook communication channels.
6. Tailor any remaining configuration fields to match your transactional guidelines.
7. Change the **State** field value to **Enabled**.

### 💡 Advanced Integration Tips
* **Risk-Free Testing:** You can safely stress-test Stripe transactions without processing real currency. Switch Odoo's payment provider mode to **Test Mode** and substitute production API keys with keys gathered from Stripe's *Test Mode* toggled view (or use an official [Stripe Sandbox Environment](https://docs.stripe.com/testing-use-cases)).
* **Multi-Company Architecture:** If your Odoo system handles [multiple companies](../../general/companies/multi_company.html) sharing a single master Stripe account, initialize and save the configuration for your first company. For the subsequent companies, copy over the exact same credentials and webhook configurations. 
  * To inspect or replicate webhook metadata, visit the [Stripe Webhooks dashboard](https://dashboard.stripe.com/webhooks). Click the targeted endpoint destination link, locate the **Signing secret** header, click the 👁️ (**Reveal secret**) icon, and duplicate this value into Odoo.

---

## Enable Apple Pay & Express Checkout

Providing fast checkout capabilities can drastically optimize mobile conversions. Odoo handles Express Checkout options like Apple Pay natively through Stripe.

1. Open your Odoo instance and navigate to **Payment Providers** ‣ **Stripe**.
2. Click into the **Configuration** tab.
3. Locate and enable the checkbox or toggle for **Allow Express Checkout**.
4. Click the dedicated **Enable Apple Pay** option to authorize device-level authentication.

---

## Transaction Lifecycles
Stripe works natively with Odoo's advanced ledger architecture to offer flexibility across sale pipelines:
* **Manual Capture:** Authorize transactions at order confirmation and capture the specific funds manually down the line.
* **Refund Support:** Initiate complete or partial refunds directly out of the Odoo workspace without switching over into the Stripe dashboard interface.