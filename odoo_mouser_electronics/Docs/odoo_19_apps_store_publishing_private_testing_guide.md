# Odoo 19 Custom Module — Apps Store Publishing & Private-Repository Testing Guide

> **Document Class:** Enterprise Standard Operating Procedure (SOP) & Technical Reference Architecture  
> **Target Framework:** Odoo 19.0 Community & Enterprise Ecosystem / Odoo Apps Marketplace  
> **Reference Module:** `TSSS Odoo AI` (`tsss_odoo_ai`)  
> **Reference Repository:** `dealwallet1/tsss_odoo_ai` (Private GitHub Repository)  
> **Governance Status:** Approved for Production & Quality Assurance  
> **Effective Date:** August 2026  

---

## Document Control & Governance Metadata

| Attribute | Technical Specification / Configuration |
|---|---|
| **Authoring Organization** | TSSS Engineering & Technical Operations |
| **Target Runtime Environment** | Odoo 19.0 (On-Premise, Odoo.sh, PaaS, SaaS) |
| **Primary Reference Module** | `tsss_odoo_ai` (TSSS Odoo AI Core Engine) |
| **Source Version Control** | Private GitHub Repository |
| **Target Release Branch** | `19.0` |
| **Delegated Vendor User** | `online-odoo` |
| **Repository Registration Pattern** | `ssh://git@github.com/<organization>/<repository>.git#19.0` |

---

## Executive Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Terminology & Foundational Concepts](#2-terminology--foundational-concepts)
3. [The Three-Tier Operational Architecture](#3-the-three-tier-operational-architecture)
4. [Prerequisite Infrastructure & Accounts](#4-prerequisite-infrastructure--accounts)
5. [Module Architecture & Manifest Specification](#5-module-architecture--manifest-specification)
   - [5.1 Standardized Directory Hierarchy](#51-standardized-directory-hierarchy)
   - [5.2 Manifest Contract & Metadata Schema (`__manifest__.py`)](#52-manifest-contract--metadata-schema-__manifest__py)
   - [5.3 Versioning Standard & Release Taxonomy](#53-versioning-standard--release-taxonomy)
6. [Repository Sanitation & Security Compliance](#6-repository-sanitation--security-compliance)
   - [6.1 Standard `.gitignore` Configuration](#61-standard-gitignore-configuration)
   - [6.2 Pre-Submission Sanitation Protocol](#62-pre-submission-sanitation-protocol)
   - [6.3 AI & Machine Learning Governance Rules](#63-ai--machine-learning-governance-rules)
7. [Source Control Setup & Branch Management](#7-source-control-setup--branch-management)
8. [Configuring Access Permissions for Private Repositories](#8-configuring-access-permissions-for-private-repositories)
9. [Apps Marketplace Repository Registration](#9-apps-marketplace-repository-registration)
10. [Repository Management & Administrative Dashboard](#10-repository-management--administrative-dashboard)
11. [Repository Scanning & Validation Lifecycle](#11-repository-scanning--validation-lifecycle)
12. [Marketplace Presentation & Quality Scoring Model](#12-marketplace-presentation--quality-scoring-model)
13. [Store Presentation Enhancement Workflow](#13-store-presentation-enhancement-workflow)
    - [13.1 Application Icon Specification (`icon.png`)](#131-application-icon-specification-iconpng)
    - [13.2 Visual Assets & Media Gallery](#132-visual-assets--media-gallery)
    - [13.3 Structured HTML Overview (`index.html`)](#133-structured-html-overview-indexhtml)
    - [13.4 Presentation Score Optimization Strategy](#134-presentation-score-optimization-strategy)
14. [Runtime Deployment & Private Verification Workflow](#14-runtime-deployment--private-verification-workflow)
15. [Enterprise Quality Assurance & Functional Test Matrix](#15-enterprise-quality-assurance--functional-test-matrix)
16. [External API Disclosures, Privacy & Data Protection](#16-external-api-disclosures-privacy--data-protection)
17. [Software Licensing & Intellectual Property Framework](#17-software-licensing--intellectual-property-framework)
18. [Commercial Governance & Pricing Standards](#18-commercial-governance--pricing-standards)
19. [Live Demonstration Instance Configuration](#19-live-demonstration-instance-configuration)
20. [Publishing State Management & Visibility Governance](#20-publishing-state-management--visibility-governance)
21. [Recommended Testing Baseline Configuration](#21-recommended-testing-baseline-configuration)
22. [Analysis of Common Technical Misconceptions](#22-analysis-of-common-technical-misconceptions)
23. [Comprehensive Pre-Release Checklist](#23-comprehensive-pre-release-checklist)
24. [Operational Troubleshooting Guide](#24-operational-troubleshooting-guide)
25. [End-to-End Execution Lifecycle](#25-end-to-end-execution-lifecycle)
26. [Official Regulatory & Technical References](#26-official-regulatory--technical-references)

---

## 1. Executive Summary

The Odoo Apps Marketplace and localized Odoo runtime application servers operate as **strictly decoupled infrastructure tiers**.

Registering a module repository on `apps.odoo.com` facilitates public distribution management, metadata validation, marketplace indexing, and store presentation scoring. Crucially, repository registration **does not automate installation, provisioning, or code execution** within any local, staging, or production Odoo runtime instance.

### 1.1 Odoo Apps Marketplace Pipeline
```text
┌──────────────────────────────────────────────┐
│       Private GitHub Source Repository       │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  Authorize 'online-odoo' Access Privileges   │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│     Register Repository SSH Connection       │
│           (apps.odoo.com/upload)             │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│    Automated Metadata & Code Scanner         │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│   Optimize Presentation Assets & Metadata    │
│    (App Icon, Banners, Screenshots, HTML)    │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  Validate Generated Marketplace Presentation │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│    Establish Publication Visibility State    │
│       (Published vs. Keep Unpublished)       │
└──────────────────────────────────────────────┘
```

### 1.2 Local / Staging Runtime Deployment Pipeline
```text
┌──────────────────────────────────────────────┐
│       Private GitHub Source Repository       │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│    Provision Repository to Addons Directory  │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│   Configure Server Config ('addons_path')    │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│     Restart Odoo Application Daemon          │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│   Execute 'Update Apps List' Operation       │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  Provision Module & Execute Test Protocols   │
└──────────────────────────────────────────────┘
```

> [!IMPORTANT]
> Successful registration on the Odoo Apps Marketplace does **not** deploy or update module code within your targeted runtime servers. Deployment to local, staging, or production instances must be managed independently via server configuration management (`addons_path`), Git deployment hooks, or Odoo.sh integration pipelines.

---

## 2. Terminology & Foundational Concepts

### 2.1 Private Git Source Repository
A version-controlled source code repository hosted on GitHub, GitLab, or Bitbucket with restricted access permissions. Odoo S.A. can clone and index private repositories **only** when explicit read privileges are granted to Odoo's automated vendor system account (`online-odoo`).

### 2.2 Published Marketplace Application
A module whose marketplace listing has been publicly activated on `apps.odoo.com`. Published applications are indexed by search engines and exposed to global Odoo users for commercial purchase or open-source download.

### 2.3 Unpublished Marketplace Application
An application registered on `apps.odoo.com` whose marketplace listing remains hidden from public search indices and catalog queries. Odoo S.A. supports unpublished applications primarily as underlying code dependencies for published modules or during formal internal testing cycles.

### 2.4 Critical Distinction: Code Isolation vs. Marketplace Visibility
> [!WARNING]
> **Source Repository Restrictions Do Not Guarantee Marketplace Privacy.**
>
> Maintaining a private GitHub repository secures your underlying source code against unauthorized access on GitHub. However, triggering the **Publish** action on `apps.odoo.com` immediately exposes the application's store presentation page and downloadable release assets to the public catalog. The Odoo Apps Marketplace does **not** natively provide an account-restricted "private store" view. To execute private validation testing on the marketplace platform, the application state must strictly remain set to **Unpublished**.

---

## 3. The Three-Tier Operational Architecture

To maintain rigorous operational hygiene during module development, validation, and staging, technical workflows must be logically compartmentalized across three independent architectural tiers:

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ TIER 1: SOURCE CONTROL & VERSION MANAGEMENT                              │
│ Private GitHub Repository (dealwallet1/tsss_odoo_ai)                     │
│ Target Release Branch: 19.0 | Delegated Access: online-odoo              │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ TIER 2: ODOO APPS MARKETPLACE PLATFORM                                   │
│ Vendor Portal (apps.odoo.com)                                            │
│ Operations: SSH Registration → Automated Scan → Metadata & Score Audit   │
│ State: Active Repository | Listing Status: Unpublished (Testing Profile) │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ TIER 3: TARGET RUNTIME INFRASTRUCTURE                                    │
│ Local, Staging, or Enterprise Odoo 19 Instance                           │
│ Operations: addons_path Provisioning → App List Refresh → Test Execution │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Prerequisite Infrastructure & Accounts

Prior to executing the publishing and validation procedures documented herein, confirm that the following prerequisite administrative parameters have been established:

- [x] **Odoo Vendor Account:** Administrative credentials for `apps.odoo.com` with confirmed vendor privileges.
- [x] **GitHub Administrative Access:** Repository-level administrative authorization to manage access policies and collaborators for the target repository.
- [x] **Compliant Odoo 19 Module:** Fully structured custom module developed strictly in accordance with Odoo 19 ORM and architectural guidelines.
- [x] **Dedicated Target Branch:** Standardized Git branch named precisely `19.0`.
- [x] **Isolated Test Instance:** Clean, fully configured Odoo 19.0 Community or Enterprise server instance.
- [x] **Standardized SSH URI Format:** Standardized remote repository URI incorporating the branch anchor:
  ```text
  ssh://git@github.com/dealwallet1/tsss_odoo_ai.git#19.0
  ```

---

## 5. Module Architecture & Manifest Specification

### 5.1 Standardized Directory Hierarchy

An Odoo 19 module submitted for marketplace validation must strictly adhere to standard Odoo directory and module packaging standards:

```text
tsss_odoo_ai/
├── __init__.py
├── __manifest__.py
├── controllers/
│   ├── __init__.py
│   └── main.py
├── models/
│   ├── __init__.py
│   └── ai_config.py
├── security/
│   ├── ir.model.access.csv
│   └── security_rules.xml
├── views/
│   ├── ai_config_views.xml
│   └── menu_items.xml
├── data/
│   └── default_data.xml
└── static/
    └── description/
        ├── icon.png          (Application Icon - 128x128 px PNG / SVG)
        ├── banner.png        (Marketplace Card Banner / Cover Image)
        ├── screenshot_1.png  (Feature View Capture 1)
        ├── screenshot_2.png  (Feature View Capture 2)
        └── index.html        (Rich HTML Marketplace Presentation Overview)
```

> [!NOTE]
> The root level of the targeted Git branch may contain either the module directory itself (e.g., `tsss_odoo_ai/`) or the raw module files directly at the repository root. Encapsulating the module within its explicit module folder is the established industry standard for multi-module repositories.

### 5.2 Manifest Contract & Metadata Schema (`__manifest__.py`)

The `__manifest__.py` file serves as the definitive structural declaration for both the Odoo ORM runtime and the Odoo Apps Marketplace indexer.

```python
# -*- coding: utf-8 -*-
{
    "name": "TSSS Odoo AI Core Engine",
    "summary": "Enterprise AI Orchestration & Conversational Workflows for Odoo 19",
    "version": "19.0.1.0.0",
    "category": "Tools",
    "author": "TSSS Engineering",
    "website": "https://example.com",
    "license": "LGPL-3",
    "depends": [
        "base",
        "web",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/ai_config_views.xml",
        "views/menu_items.xml",
    ],
    "images": [
        "static/description/banner.png",
        "static/description/screenshot_1.png",
        "static/description/screenshot_2.png",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
```

#### Manifest Parameter Governance Matrix

| Manifest Descriptor | Enforcement Level | Technical Requirement & Functional Constraint |
|---|---|---|
| `name` | **Mandatory** | Official application title displayed on marketplace index cards and runtime menus. |
| `version` | **Mandatory** | Semantic version string. Must strictly begin with the target major release (`19.0.1.0.0`). |
| `license` | **Mandatory** | Legal licensing descriptor (`LGPL-3`, `OPL-1`, `GPL-3`, etc.). Must match repository license. |
| `depends` | **Mandatory** | Explicit list of technical module identifiers required prior to module installation. |
| `summary` | **Required for Quality** | Concise one-line executive summary displayed on search results cards. |
| `images` | **Required for Quality** | Ordered array of relative file paths for marketplace gallery assets. |
| `application` | Recommended | Boolean flag (`True` designates a standalone application; `False` indicates a supporting addon). |
| `price` | Optional | Commercial pricing numeric value (e.g. `49.99`). Omit entirely for open-source modules. |
| `currency` | Optional | ISO currency code (`EUR` or `USD`). Defaults to `EUR` if omitted. |
| `live_test_url` | Optional | Fully qualified HTTPS URL routing to a sanitized, interactive demonstration database. |

### 5.3 Versioning Standard & Release Taxonomy

Odoo S.A. enforces a rigid versioning taxonomy for custom modules. Version strings must incorporate the target Odoo major version as a prefix:

$$\text{Taxonomy: } \texttt{<Odoo\_Major\_Version>.<Major\_Release>.<Minor\_Feature>.<Patch\_Level>.<Build\_Sequence>}$$

- **Odoo 19 Initial Release:** `19.0.1.0.0`
- **Minor Feature Increment:** `19.0.1.1.0`
- **Patch / Bug Fix Release:** `19.0.1.1.1`

---

## 6. Repository Sanitation & Security Compliance

Prior to delegating repository access to external platform scanners, execute rigorous security sanitation to protect intellectual property and sensitive credentials.

### 6.1 Standard `.gitignore` Configuration

Establish a strict `.gitignore` file at the root of the source repository:

```gitignore
# Byte-compiled & execution cache artifacts
__pycache__/
*.py[cod]
*$py.class

# Virtual environment infrastructure
.venv/
venv/
ENV/
env/

# Security credentials & environment parameters
.env
.env.*
*.pem
*.key
*.crt

# IDE & workspace configurations
.idea/
.vscode/
*.swp
*.swo

# Diagnostic log files & database dumps
*.log
*.sqlite
*.db
*.dump
*.sql

# System metadata artifacts
.DS_Store
Thumbs.db
```

### 6.2 Pre-Submission Sanitation Protocol

- [ ] Audit repository commit history to ensure zero hardcoded API secrets, OAuth tokens, or private private keys exist.
- [ ] Remove all transient bytecode cache directories (`__pycache__`) and compiled binaries (`.pyc`).
- [ ] Verify that environment-specific configuration files (`.env`, `odoo.conf`) are excluded from source control.
- [ ] Confirm no customer data, sensitive database dumps, or internal corporate records are contained in test fixtures.

### 6.3 AI & Machine Learning Governance Rules

For modules delivering artificial intelligence, vector embeddings, or machine learning capabilities (such as `tsss_odoo_ai`), strict compliance policies apply:

> [!CAUTION]
> **Odoo Marketplace Regulatory Restrictions on Binaries & AI Protocols:**
> 1. **Prohibition of Executable Binaries:** Modules must not bundle, download, or execute compiled native binaries (`.exe`, `.so`, `.dll`) or unverified shell scripts.
> 2. **Prohibition of Obfuscation:** Source code must remain transparent. Encrypted, obfuscated, or compiled Python (`.pyc`-only) modules will trigger immediate platform rejection.
> 3. **Externalization of Model Artifacts:** Heavy ML weights, vector models, or binary neural net checkpoints must be hosted on dedicated storage infrastructure (e.g. Hugging Face, AWS S3) and accessed via HTTPS APIs rather than committed to Git.
> 4. **Data Transmission Transparency:** Outbound data transfers to external Large Language Model (LLM) endpoints (e.g., OpenAI, Anthropic, Google Gemini) must be explicitly disclosed within `static/description/index.html`.

---

## 7. Source Control Setup & Branch Management

Execute standard Git commands to initialize, structure, and push the target release branch:

```bash
# Initialize local source repository
git init

# Stage sanitized codebase
git add .
git commit -m "feat(core): initialize Odoo 19 TSSS AI module architecture"

# Establish mandatory 19.0 target branch
git branch -M 19.0

# Configure secure SSH remote and execute initial push
git remote add origin git@github.com:dealwallet1/tsss_odoo_ai.git
git push -u origin 19.0
```

---

## 8. Configuring Access Permissions for Private Repositories

To enable automated scanning of private GitHub repositories by Odoo S.A., read permissions must be explicitly delegated to Odoo's automated platform account.

### Administrative Delegation Procedure

1. Access the target repository settings on GitHub: `https://github.com/dealwallet1/tsss_odoo_ai`.
2. Select **Settings** $\rightarrow$ **Collaborators and teams** (or **Access**).
3. Click **Add people**.
4. Input the exact delegated GitHub system username:
   ```text
   online-odoo
   ```
   > [!IMPORTANT]
   > Confirm that access is granted specifically to `online-odoo`. Do **not** select `odoo-online` or secondary third-party user handles.
5. Assign **Read** access permissions and finalize the collaborator invitation.

```text
GitHub Repository Settings 
  └── Access Governance / Collaborators 
        └── Invite User: "online-odoo" [Access Level: Read]
```

---

## 9. Apps Marketplace Repository Registration

1. Authenticate with administrative credentials on [apps.odoo.com](https://apps.odoo.com).
2. Navigate to the repository registration portal: [apps.odoo.com/apps/upload](https://apps.odoo.com/apps/upload).
3. Select **Register a new repository**.
4. Input the standardized SSH URI containing the explicit branch anchor:

```text
ssh://git@github.com/dealwallet1/tsss_odoo_ai.git#19.0
```

> [!NOTE]
> The mandatory URI syntax enforced by Odoo S.A. is structured as follows:  
> `ssh://git@<hostname>/<organization>/<repository>.git#<target_branch>`

---

## 10. Repository Management & Administrative Dashboard

Registered repositories are administered via the **My Repos** control console:

```text
https://apps.odoo.com/apps/modules
```

### Management Control Functions

| Control Option | System Function & Operational Impact |
|---|---|
| **Edit** | Modifies registered SSH connection string or changes target branch specification. |
| **Scan** | Forces Odoo's automated scanner to pull the latest commit from `19.0` and execute validation protocols. |
| **Active (Toggle)** | Toggles automated background scanning services for the target repository. |
| **Unpublish all apps** | Instantly transitions all applications within the repository to the **Unpublished** state. Required for private staging. |
| **Publish all apps** | Exposes all validated applications in the repository to the public marketplace catalog. |

---

## 11. Repository Scanning & Validation Lifecycle

Triggering a **Scan** initiates an automated compliance pipeline evaluating manifest integrity, AST syntax correctness, dependency resolution, and presentation completeness.

```text
               ┌─────────────────────────────────────┐
               │    Trigger Manual Repository Scan   │
               └──────────────────┬──────────────────┘
                                  │
                                  ▼
               ┌─────────────────────────────────────┐
               │  Odoo System Clones Target Branch   │
               └──────────────────┬──────────────────┘
                                  │
                                  ▼
               ┌─────────────────────────────────────┐
               │   Execute Code & Metadata Audits    │
               └──────────────────┬──────────────────┘
                                  │
         ┌────────────────────────┴────────────────────────┐
         ▼                                                 ▼
┌─────────────────────────────────┐       ┌─────────────────────────────────┐
│ Validation Warnings / Failures  │       │  Scan Execution Successful      │
└────────┬────────────────────────┘       └────────────────┬────────────────┘
         │                                                 │
         ▼                                                 ▼
┌─────────────────────────────────┐       ┌─────────────────────────────────┐
│ Remediate Codebase in Local Git │       │ App Presentation Record Built   │
└────────┬────────────────────────┘       └─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ Commit & Push Fixes to '19.0'   │
└────────┬────────────────────────┘
         │
         └────────────────┐
                          │
                          ▼
               ┌─────────────────────────────────────┐
               │ Re-Trigger Repository Scan Protocol │
               └─────────────────────────────────────┘
```

---

## 12. Marketplace Presentation & Quality Scoring Model

Upon successful scan execution, Odoo S.A. generates a dedicated Marketplace Presentation Page for `TSSS Odoo AI Core Engine v19.0`.

Presentation pages are automatically audited and assigned a **Quality Rating (0 to 5 Stars)** evaluated against five core presentation criteria:

```text
Marketplace Presentation Quality Score (0 to 5 Stars)
 ├── 1. Application Icon Provisioning (Presence of valid static/description/icon.png)
 ├── 2. Card Banner Asset (Declaration of banner image in manifest 'images' key)
 ├── 3. License Metadata (Specification of valid OSI/Odoo license string)
 ├── 4. Rich HTML Overview (Presence of formatted static/description/index.html)
 └── 5. Community Feedback & Rating Aggregation
```

---

## 13. Store Presentation Enhancement Workflow

### 13.1 Application Icon Specification (`icon.png`)

Ensure an application icon is provisioned at the precise relative path:
```text
static/description/icon.png
```
- **Technical Specifications:** PNG format, 128x128 pixels resolution (or scalable vector SVG).
- **Design Guidelines:** High-contrast, professional visual mark on a clean background.

### 13.2 Visual Assets & Media Gallery

Provision graphic assets within `static/description/` and register them explicitly in `__manifest__.py`:

```python
"images": [
    "static/description/banner.png",
    "static/description/screenshot_1.png",
    "static/description/screenshot_2.png",
],
```

- **`banner.png`**: Primary marketplace presentation banner. Recommended aspect ratio 16:9 (e.g., 1200x630 pixels).
- **`screenshot_1.png`**, **`screenshot_2.png`**: Crisp screen captures illustrating core functional workflows.

### 13.3 Structured HTML Overview (`index.html`)

Create a responsive, Bootstrap-compliant overview document at `static/description/index.html`:

```html
<section class="container py-4">
    <div class="row text-center mb-4">
        <div class="col-12">
            <h2 class="display-4 fw-bold" style="color: #714B67;">TSSS Odoo AI Core Engine</h2>
            <p class="lead text-muted">Enterprise-Grade Artificial Intelligence & Automation Infrastructure for Odoo 19</p>
        </div>
    </div>

    <div class="row my-4">
        <div class="col-md-6">
            <h3 class="fw-bold">Core Architectural Features</h3>
            <ul class="list-unstyled">
                <li><i class="fa fa-check text-primary me-2"></i> Automated AI orchestration within core Odoo models.</li>
                <li><i class="fa fa-check text-primary me-2"></i> Context-aware conversational assistant interfaces.</li>
                <li><i class="fa fa-check text-primary me-2"></i> Seamless multi-company and multi-currency compatibility.</li>
            </ul>
        </div>
        <div class="col-md-6">
            <h3 class="fw-bold">Technical System Requirements</h3>
            <p><strong>Target Framework:</strong> Odoo 19.0 (Community / Enterprise)</p>
            <p><strong>External API Connectivity:</strong> OpenAI / Anthropic / Custom Enterprise Endpoints</p>
        </div>
    </div>
</section>
```

> [!WARNING]
> **Marketplace HTML Presentation Constraints:**
> - Embedded JavaScript (`<script>` blocks) is **strictly prohibited**.
> - External CSS links are blocked. Layouts must utilize standard Odoo Bootstrap utilities and inline styles.
> - Content must be authored in primary **English**.
> - Outbound hyperlinks are restricted (approved exceptions include embedded YouTube demonstrations and Microsoft Teams documentation).

### 13.4 Presentation Score Optimization Strategy

To systematically secure a **5/5 Star Quality Rating**:
1. Commit `icon.png`, `banner.png`, screenshots, and `index.html`.
2. Push updates to the GitHub `19.0` branch:
   ```bash
   git add static/description/
   git commit -m "docs(store): optimize marketplace presentation assets and index.html"
   git push origin 19.0
   ```
3. Re-trigger the **Scan** action via the **My Repos** console.

---

## 14. Runtime Deployment & Private Verification Workflow

To validate the module functionally within a targeted Odoo 19 runtime environment:

1. Clone or link the source repository into the designated custom addons directory:
   ```text
   C:\TSSS\dealwallet_odoo_addons\tsss_odoo_ai
   ```
2. Update `odoo.conf` to include the target addons path:
   ```ini
   [options]
   addons_path = C:\TSSS\odoo19\odoo\addons,C:\TSSS\dealwallet_odoo_addons
   ```
3. Restart the Odoo application daemon.
4. Authenticate as an Administrator and activate **Developer Mode** (`Settings` $\rightarrow$ `Activate Developer Mode`).
5. Access the **Apps** menu, execute **Update Apps List**, remove default filters, locate `TSSS Odoo AI Core Engine`, and click **Install**.

---

## 15. Enterprise Quality Assurance & Functional Test Matrix

Execute the following standardized testing protocol prior to authorized release:

| Case ID | Functional Verification Scope | Execution Procedure | Expected Acceptance Criteria | Status |
|---|---|---|---|---|
| **TC-01** | Provisioning Hygiene | Provision on a clean Odoo 19 database | Module installs cleanly without dependency failure | [ ] |
| **TC-02** | Schema Migration | Execute `odoo-bin -u tsss_odoo_ai` | Database schema updates cleanly without migration errors | [ ] |
| **TC-03** | Daemon Lifecycle | Restart server daemon post-installation | Server initializes cleanly without import tracebacks | [ ] |
| **TC-04** | RBAC Isolation | Authenticate as a Standard User | Access granted to permitted views; restricted views blocked | [ ] |
| **TC-05** | Record Security | Evaluate record-level security rules | `ir.rule` filters multi-tenant records correctly | [ ] |
| **TC-06** | Core Execution | Trigger primary AI processing workflows | Business logic executes per functional specifications | [ ] |
| **TC-07** | Parameter Storage | Persist settings via `res.config.settings` | Configuration values save accurately in `ir.config_parameter` | [ ] |
| **TC-08** | Clean De-provisioning | Uninstall module via Apps console | Module uninstalls cleanly; zero orphaned dependencies remain | [ ] |
| **TC-09** | Re-provisioning | Re-install module immediately post-uninstall | Re-installation completes without unique key constraints | [ ] |
| **TC-10** | API Resilience | Terminate API connectivity / supply invalid key | Graceful error handling displayed; zero server crashes | [ ] |
| **TC-11** | Multi-Company Isolation | Switch active company context | Data remains isolated strictly per active company ID | [ ] |
| **TC-12** | API Deprecation Audit | Inspect `odoo.log` for deprecation flags | Zero Odoo 19 ORM API deprecation warnings logged | [ ] |
| **TC-13** | Frontend Asset Audit | Inspect Web Browser Developer Console | Zero JavaScript/OWL asset compilation or runtime errors | [ ] |
| **TC-14** | Log Cleanliness Audit | Monitor `odoo.log` under stress load | Log file remains free of uncaught tracebacks | [ ] |

---

## 16. External API Disclosures, Privacy & Data Protection

If your custom module communicates with external web services or AI endpoints (e.g., OpenAI, Anthropic, Twilio, Razorpay, Google Cloud):

1. **Disclosure Requirement:** All external service dependencies must be explicitly disclosed within `static/description/index.html`.
2. **Data Governance Statement:** Technical documentation must explicitly specify:
   - Specific data attributes transmitted externally.
   - Business justification for external transmission.
   - Endpoint security protocols (HTTPS / TLS 1.3).
   - Credential encryption standards (e.g., system parameter encryption).
3. **Explicit Opt-In Controls:** Modules must provide explicit configuration toggles enabling system administrators to authorize external API communications prior to execution.

---

## 17. Software Licensing & Intellectual Property Framework

Odoo S.A. enforces strict license compliance rules. Modules must declare an OSI-approved or Odoo-compliant license key in `__manifest__.py`:

```python
"license": "LGPL-3",
```

### Approved Licensing Paradigms

- **`LGPL-3`** (GNU Lesser General Public License v3.0): Industry standard for open-source and commercial community addons. Permits integration without forcing viral copyleft compliance.
- **`OPL-1`** (Odoo Proprietary License v1.0): Mandatory license for paid, proprietary modules distributed commercially via the Odoo Apps Marketplace. Prohibits unauthorized redistribution.
- **`AGPL-3`**: Strict copyleft license for open-source distributions.

> [!IMPORTANT]
> Verify that all third-party Python packages, JavaScript libraries, or external assets embedded within your module possess license terms compatible with your declared manifest license.

---

## 18. Commercial Governance & Pricing Standards

For modules commercialized via `apps.odoo.com`:

1. **Manifest Pricing Keys:**
   ```python
   "price": 49.99,
   "currency": "EUR",
   ```
2. **Authorized Currencies:** `EUR` and `USD`.
3. **Minimum Commercial Threshold:** EUR 9.00 (or equivalent USD).
4. **Marketplace Price Parity:** Vendor terms dictate that prices listed on the Odoo Apps Marketplace must be **equal to or lower than** prices listed for the same module on external third-party software stores.

---

## 19. Live Demonstration Instance Configuration

To provide potential clients with an interactive demonstration environment, declare a live test instance URL in `__manifest__.py`:

```python
"live_test_url": "https://demo.example.com/web?db=odoo19_demo",
```

Ensure demonstration instances are hardened, protected against unauthorized administrative mutation, and configured to reset automatically at periodic intervals.

---

## 20. Publishing State Management & Visibility Governance

Administer application visibility states via the **My Repos** management console:

```text
┌──────────────────────────────────────────────────────────────────┐
│ REPOSITORY REGISTRATION STATUS: ACTIVE                           │
├──────────────────────────────────┬───────────────────────────────┤
│   UNPUBLISHED STATE (Default)    │        PUBLISHED STATE        │
│                                  │                               │
│ • Visible exclusively within the │ • Publicly visible across the │
│   Vendor Management Console.     │   Odoo Apps Marketplace.      │
│ • Recommended for internal QA,   │ • Searchable and downloadable │
│   staging, and release testing.  │   by global Odoo users.       │
│ • Source repository remains      │ • Source repository remains   │
│   private on GitHub.             │   private on GitHub.          │
└──────────────────────────────────┴───────────────────────────────┘
```

- To maintain isolation during development, select **Unpublish all apps from this repo**.
- To execute formal public distribution, select **Publish all apps from this repo** (or activate publication individually via the application record view).

---

## 21. Recommended Testing Baseline Configuration

For secure internal verification of `TSSS Odoo AI Core Engine` prior to market launch, maintain the following baseline governance state:

| Control Domain | Mandated Configuration State |
|---|---|
| **GitHub Source Repository** | `PRIVATE` |
| **GitHub Access Delegation** | `online-odoo` invited with Read privileges |
| **Target Release Branch** | `19.0` |
| **Odoo Marketplace Status** | `ACTIVE` |
| **Marketplace Scan Result** | `PASSED (Zero fatal errors)` |
| **Presentation Score** | `5/5 Stars` |
| **Application Listing State** | `UNPUBLISHED` |
| **Runtime Test Status** | `VERIFIED (100% Pass Rate across TC-01 to TC-14)` |

---

## 22. Analysis of Common Technical Misconceptions

### Misconception 1: "Repository registration automatically provisions the module to local Odoo servers."
**Fact:** Incorrect. Marketplace registration manages store metadata and distribution cataloging exclusively. Local deployment requires manual or automated provisioning to the target server's `addons_path` followed by executing **Update Apps List**.

### Misconception 2: "Maintaining a private GitHub repository ensures the marketplace listing is private."
**Fact:** Incorrect. Source repository privacy protects your underlying code on GitHub. Clicking **Publish** on `apps.odoo.com` instantly makes the store listing and release packages publicly accessible worldwide.

### Misconception 3: "An 'Active' repository status indicates public application publication."
**Fact:** Incorrect. `Active` signifies solely that Odoo's platform service is monitoring the Git branch for commits. Marketplace visibility is governed independently via the **Publish / Unpublish** toggle.

### Misconception 4: "A presentation score of 3/5 Stars indicates underlying Python code defects."
**Fact:** Incorrect. Quality scores evaluate marketplace presentation completeness (missing icons, missing HTML overview, missing cover image, or missing license key). Code validity is verified exclusively via runtime execution and log audits.

### Misconception 5: "Manifest metadata can be edited directly within the Apps Marketplace Web UI."
**Fact:** Incorrect. The marketplace engine reads metadata dynamically from version control. All changes to manifests, icons, documentation, or code must be committed to Git, pushed to `19.0`, and re-scanned.

---

## 23. Comprehensive Pre-Release Checklist

### Phase 1: Source Control & Security Audit
- [ ] Source repository visibility configured strictly to **Private** on GitHub.
- [ ] Dedicated `19.0` target release branch checked out and established as remote tracking branch.
- [ ] Delegated system account `online-odoo` granted Read permissions on GitHub.
- [ ] `.gitignore` verified to exclude byte-compiled cache, `.env` files, and IDE workspace configs.
- [ ] Codebase audited to confirm total absence of hardcoded passwords, private keys, or API tokens.

### Phase 2: Codebase & Manifest Integrity
- [ ] `__init__.py` provisioned in repository root and all Python sub-packages.
- [ ] `__manifest__.py` syntactically validated containing `name`, `version`, `license`, and `depends`.
- [ ] Version string prefixed correctly with target major release (`19.0.1.0.0`).
- [ ] `security/ir.model.access.csv` provisioned with complete ACL coverage across all custom models.
- [ ] All XML views, security rules, and data files validated against Odoo 19 schema rules.

### Phase 3: Marketplace Presentation Excellence
- [ ] Application icon provisioned at `static/description/icon.png` (128x128 px PNG / SVG).
- [ ] Presentation banner provisioned at `static/description/banner.png` and declared in `images`.
- [ ] High-resolution functional screen captures provisioned and registered in `images`.
- [ ] Responsive HTML overview authored at `static/description/index.html` (Bootstrap compliant, zero JS).
- [ ] Outbound API disclosures and data protection terms explicitly documented.

### Phase 4: Marketplace Validation & Scan Audit
- [ ] Repository registered on `apps.odoo.com/apps/upload` via standardized SSH URI.
- [ ] Automated **Scan** protocol executed successfully with zero validation errors.
- [ ] Presentation score optimized to a perfect **5/5 Stars**.
- [ ] Application listing state explicitly set to **Unpublished** for private validation.

### Phase 5: Runtime Quality Assurance
- [ ] Module deployed and initialized successfully on a clean Odoo 19 test instance.
- [ ] Executed 100% of functional test cases in [Section 15](#15-enterprise-quality-assurance--functional-test-matrix) with pass status.
- [ ] Verified server log (`odoo.log`) remains free of tracebacks and API deprecation flags.

---

## 24. Operational Troubleshooting Guide

### Issue 1: Automated Repository Scan Fails on `apps.odoo.com`
**Root Cause Analysis & Remediation:**
- **Access Delegation Failure:** Confirm that `online-odoo` has accepted the collaborator invitation on GitHub.
- **URI Formatting Defect:** Verify that the registration URI strictly adheres to `ssh://git@github.com/<org>/<repo>.git#19.0`.
- **Target Branch Absence:** Confirm that branch `19.0` has been pushed to the remote repository.
- **Manifest Compilation Error:** Execute local compilation verification: `python -m py_compile __manifest__.py`.

### Issue 2: Module Unregistered in Local Odoo Application Directory
**Root Cause Analysis & Remediation:**
- **Addons Path Misconfiguration:** Verify that `odoo.conf` contains the exact absolute path to the module parent directory.
- **Daemon Process Persistence:** Confirm the Odoo server daemon was restarted following configuration updates.
- **Filter Persistence:** Ensure Developer Mode is active, click **Update Apps List**, and clear the default `Apps` search filter.

### Issue 3: Presentation Score Blocked Below 5 Stars
**Root Cause Analysis & Remediation:**
- Access the application record on `apps.odoo.com` to inspect flagged presentation deficiencies:
  - Provision missing application icon (`static/description/icon.png`).
  - Register card banner in manifest: `"images": ["static/description/banner.png"]`.
  - Declare valid license key in manifest: `"license": "LGPL-3"`.
  - Author rich overview document (`static/description/index.html`).
- Commit changes, push to `19.0`, and re-trigger **Scan**.

### Issue 4: Historical Application Record Persists Post-Deletion
**System Governance Note:** Odoo S.A. intentionally retains historical application records on `apps.odoo.com` for dependency resolution and licensing compliance. To request permanent purge of an unpurchased test record, submit a formal request to `apps@odoo.com`.

---

## 25. End-to-End Execution Lifecycle

```text
[Phase 1] Develop Odoo 19 Custom Module (tsss_odoo_ai)
    │
[Phase 2] Sanitize Repository & Establish .gitignore Rules
    │
[Phase 3] Push Codebase to Private GitHub Repository (Branch: 19.0)
    │
[Phase 4] Delegate Read Access to 'online-odoo' System Account
    │
[Phase 5] Register Repository SSH URI on apps.odoo.com/apps/upload
    │
[Phase 6] Execute Repository Scan & Resolve Metadata Deficiencies
    │
[Phase 7] Provision Presentation Assets (Icon, Banner, Screenshots, HTML)
    │
[Phase 8] Push Presentation Updates & Achieve 5/5 Star Rating
    │
[Phase 9] Deploy to Target Odoo 19 Runtime Instance & Refresh App List
    │
[Phase 10] Execute Full Functional Test Matrix (TC-01 through TC-14)
    │
[Phase 11] Establish Final Listing State (Unpublished for QA / Published for Production)
```

---

## 26. Official Regulatory & Technical References

- **Odoo Apps Marketplace Portal:** [https://apps.odoo.com/apps/upload](https://apps.odoo.com/apps/upload)
- **Odoo Apps Frequently Asked Questions:** [https://apps.odoo.com/apps/faq](https://apps.odoo.com/apps/faq)
- **Odoo Apps Vendor Governance Guidelines:** [https://apps.odoo.com/apps/vendor-guidelines](https://apps.odoo.com/apps/vendor-guidelines)
- **Odoo 19 Developer Documentation:** [https://www.odoo.com/documentation/19.0/developer.html](https://www.odoo.com/documentation/19.0/developer.html)

---

> **Governance Maintenance Notice:**  
> This Standard Operating Procedure must be reviewed and re-validated whenever Odoo S.A. publishes updates to its vendor governance policies, marketplace scanning algorithms, or Odoo 19 core architecture framework specifications.
