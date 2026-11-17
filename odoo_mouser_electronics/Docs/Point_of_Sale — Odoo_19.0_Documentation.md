# Point of Sale — Odoo 19.0 Documentation

Odoo Point of Sale (POS) is an all-in-one management application designed specifically for retail shops, bars, and restaurants. It is entirely web-browser-based, enabling it to run seamlessly on any device (desktop, tablet, or mobile). It is architected to remain completely functional even during temporary network or internet outages. In addition to traditional merchant workflows, Odoo POS natively supports a self-ordering mode, allowing clients to place orders and make payments using an interactive in-store kiosk or via their own personal mobile devices.

---

## 1. Core POS Workflows & Register Operations

### POS Creation & Configuration
* **Performance Tip:** To optimize the performance of your POS browser tabs, disable the "Memory Saver" setting within Google Chrome.
* **Preconfigured Configurations:** If no setup exists in your database, the Point of Sale Dashboard displays specialized preconfigured business cards (e.g., Shop, Bar, Restaurant) to deploy settings tailored to that business type instantly.
* **Custom Initialization:** To spin up a new shop or manage global options, navigate to `Point of Sale ‣ Configuration ‣ Point of Sales` or click `+ New Shop` directly inside the configuration header.
* **Accounting Integrity:** Assigning a unique, dedicated cash payment method and isolated cash journal to each point of sale ensures clear audit trails and separates accounting entries across distinct registers.

### Managing Register Sessions
* **Opening Control:** Launch your POS by heading to `Point of Sale ‣ Dashboard` and clicking **Open Register** on the target card. Ensure the opening cash drawer balance is correct in the popover before fully opening the terminal session.
* **Register Interface:** The checkout interface is divided into three functional areas: the product selector, the active shopping cart layout, and the dynamic keypad (numpad).
* **Executing Sales:** Select products to append them to the cart. Use the numpad controls (`Qty` to alter item counts, `Price` to overwrite product valuation, and `%` to apply markdown reductions). Click **Payment**, choose your payment method, and select **Validate** to clear the cart and finalize the sale.
* **Internal Routing Notes:** To attach a note to an entire transaction, ensure no item is highlighted in the cart and click `Note`. To add a message to a specific line item, highlight the item in the cart first before clicking `Note`.
* **Processing Returns & Refunds:** To execute a return from the register, click the vertical ellipsis icon, select `Refund`, locate the original entry in the `Paid` orders list, input the target quantity, and proceed to the payment interface to return the funds.
* **Closing Control:** To shut down a register, click the hamburger menu icon and select `Close Register`. Use the money icon to verify and input physical currency counts before clicking the final `Close Register` button, which automatically reconciles and posts financial entries.

---

## 2. Product & Category Configurations

### Backend and Frontend Creation
* **Creation Adaptability:** Products can be managed from the backend database or added directly mid-session by navigating to the register's hamburger menu and clicking `Create Product`.
* **Point of Sale Specific Parameters:** Within the product form's *Point of Sale* tab, you can fine-tune specialized retail configurations:
  * Enable **To Weigh With Scale** for items requiring integrated scale readouts.
  * Map POS-specific classification categories and associate custom display colors to group and highlight inventory in the register.
  * Toggle **Available in Self Order** to make specific variants visible to self-service kiosk environments.
  * Configure **POS Optional Products** in the cross-sell area to auto-prompt operators with companion products upon cart insertion.
* **Product Combos:** To package menu bundles, configure standalone combo item variations under your products menu first, create a parent product, alter its *Product Type* to **Combo**, and link your pre-built combo choices.
* **Live In-Register Inspections:** Long-pressing any product button in the register opens a data panel showing real-time available and forecasted inventory, warehouse levels, replenishment timelines, costs, and profit margins.

---

## 3. Hardware, Network, & Peripherals

Odoo POS supports broad peripheral integration, directly interfacing with receipt printers, cash registers, scale hardware, customer face-plates, barcode inputs, and digital pricing displays.

* **Local Network Access:** Enables the application to coordinate directly with local network peripherals (like ePOS hardware) over standard browsers without relying on local SSL setups.
* **IoT Box Synchronization:** Connecting an IoT box lets you coordinate legacy or standard hardware components seamlessly (such as physical scales, registers, or scanners).
* **Digital Electronic Shelf Labels:** Integrates directly with the Pricer infrastructure platform to push product pricing modifications dynamically to physical shelf-edge displays.
* **Scales & Displays:** Secondary customer displays show checkout lines and prices in real time, while integrated scale settings can be adapted to fulfill strict European legal metrology compliance parameters.

---

## 4. Retail-Specific Shop Features

### Quotations & Sales Orders
* **Settle Backend Documents:** Register operators can click the vertical ellipsis icon and select `Quotation/Order` to pull open orders initiated by your backend sales teams. 
* **Flexible Settle Types:** Orders can be cleared completely by clicking `Settle the order`, or partially handled by applying a fixed amount or percentage-based down payment.

### Ship Later Workflows
* **Configuration:** To delay fulfillment, pick a customer profile and toggle the **Ship Later** option on the payment layout screen.
* **Automated Logistical Execution:** Input a specified target shipping window and complete the checkout; the backend automatically routes an active delivery order request from your fulfillment warehouse directly to the client's destination address.

### Barcode Automation
* **Execution Utilities:** Barcode workflows dramatically improve speed, allowing cashier identification badge check-ins, direct item cataloging, and markdown management.
* **Nomenclature Matching Rules:** The software matches read patterns sequentially against pre-defined rules. For instance, setting up discount markdown stickers using standard prefixes (like pattern `22{NN}`) lets the POS interpret the barcode as a price deduction rather than a new stock SKU.

---

## 5. Restaurant & Hospitality Features

### Floor Plans & Bookings
* **Visual Map Layouts:** Build explicit restaurant zone floor maps by defining zone titles, embedding high-resolution background maps, and customizing table seats, shapes (round vs. square), colors, and identification markers.
* **Reservation Pipelines:** Activating table **Booking** parameters inside the POS interface settings adds an appointment tracking engine. Staff can create guest profiles and update reservations across pipeline milestones like *Booked*, *Checked-In*, or *No Show*.

### Table Routing & Guest Bills
* **Kitchen Order Controls:** Assign orders to distinct locations using `Set Table` or track tabs using `Set Tab`. Clicking `Send` dispatches line items directly to physical preparation printers or routes them electronically to a paperless *Kitchen Display* monitor application.
* **Bill Splitting Tools:** Click `Actions ‣ Split` to separate a combined check, allowing you to process individual item payments or isolate distinct covers into independent sub-orders.
* **Integrated Gratuities:** Link Adyen or Stripe payment terminals to enable post-payment tipping workflows, offering customers quick-select tip thresholds (15%, 20%, or 25%) directly on the terminal.

---

## 6. Payment Gateways & Customer Credit Accounts

### Customer Balances & Store Credit
* **Account Credit:** The customer account feature allows recurring clients to use store credit or complete register transactions on account, tracking debts for subsequent consolidation.
* **Enforcing Limits:** To minimize credit risks, configure a *maximum sales credit* cap. Exceeding this boundary highlights the customer profile in orange and flags a warning icon, though it does not completely lock cashiers from completing the sale if authorized.
* **Account Deposits:** Cashiers can top up store credit on a profile by selecting a customer, clicking the hamburger menu icon, selecting `Deposit money`, and inputting the funding value via the terminal.

### Debt Settlement and Tracking
* **Clear Outstanding Accounts:** Outstanding customer balances can be settled at the register by clicking the customer's menu, selecting `Settle orders` or `Settle invoices`, and processing payment for the selected items.
* **Backend Audit Tools:** Run the *Customer Statement* reports via `Point of Sale ‣ Orders ‣ Customers` to monitor accumulated debts and review statements.