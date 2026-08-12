# ⚖️ Despacho Laboral — Complete System & Features Document

> **System:** Web application for managing labor law cases at a law firm in Tijuana, Mexico
> **Product name:** Conciliación Laboral Tijuana — Despacho Laboral
> **Stack:** Django 5.x · Tailwind CSS · HTMX · PostgreSQL/SQLite · Celery + Redis · Selenium
> **Last updated:** August 2026

---

## 1. What the System Does

`Despacho Laboral` is a **case-management (CRM + legal workflow) platform** for a labor
law practice. It manages the complete life cycle of a labor claim — from the first client
contact, through the mandatory pre-trial conciliation stage with the *Centro de
Conciliación Laboral (CCL)* of Baja California, up to settlement (convenio) or filing a
formal lawsuit (demanda laboral).

Beyond case tracking, the platform automates the most repetitive and error-prone parts of
the practice:

- **Legal benefit calculations** (aguinaldo, vacation premium, seniority premium,
  constitutional severance, etc.) computed automatically from Mexican labor law (LFT).
- **Legal document generation** from reusable HTML templates (machotes) with automatic
  data injection.
- **Automated submission of conciliation requests** to the official BC government portal
  (`app.conciliacionbc.gob.mx`) — both server-side and via a companion Chrome extension.
- **WhatsApp notifications** to clients (manual, automatic per state change, and reminders).
- **A full finance module** (payments, expenses, payroll, commissions, cash registers,
  partner loans, profit distribution) organized per office and per work week.

---

## 2. Users, Roles & Permissions

### 2.1 Roles (5)

| Role | Key | Scope |
|------|-----|-------|
| **Superadmin** | `superadmin` | Full access: Django admin, all dashboards, permission matrix, user management |
| **Administrativo** | `admin` | Sees all cases, productivity reports, totals, Excel exports, Django admin access |
| **Asesor** | `asesor` | Only sees and edits **his own** cases; personal dashboard with stats |
| **Abogada** | `abogada` | Dedicated dashboard for the firm's attorney (case overview & document focus) |
| **Finanzas** | `finanzas` | Financial dashboard and finance module access (counts as admin for permissions) |

### 2.2 Profile capabilities (`UserProfile`)

Each user profile additionally has:

- **`puede_generar_documentos`** — flag granting access to the legal document generators
  (demanda, machotes, legal documents). Off by default.
- **`api_token`** — personal API token used by the Chrome extension to authenticate
  against the app's extension API. Auto-generated on profile creation and can be
  regenerated (invalidating the old one) from the *Extensión de Chrome* config page.

### 2.3 Permission audit (`PermisoAuditLog`)

Every time a superadmin/admin changes a user's role, document permissions, or other
privileges, an **audit entry** is recorded: who was modified, who modified them, the
action (`cambio_rol`, `cambio_docs`, `mixto`), and the detail (e.g. `Rol: asesor → admin`).

### 2.4 Superadmin module

- **Superadmin dashboard** — overview panel for platform administration.
- **Permission matrix** (`matriz_permisos`) — grid to manage every user's role and
  document-generation permission, with **Excel export**.
- **Load demo data** — one-click seeding of demo users/cases for testing.

### 2.5 Auth & security

- Login / logout, full **password reset** flow via email (SMTP configurable; console
  backend by default in dev).
- Redirect to the correct dashboard automatically per role after login.
- Production hardening: HTTPS redirect, secure cookies, Railway domain auto-detection,
  env-driven `DEBUG`/`SECRET_KEY`/`ALLOWED_HOSTS`.

---

## 3. Case Management (Módulo Expedientes)

### 3.1 Clients (`Cliente`)

Rich client record built specifically for labor conciliation:

- **Identity:** name, **CURP** (unique), RFC, phone, WhatsApp, email, birth date, gender.
- **Home address:** street, number, ZIP, colonia — assembled into `direccion_completa`.
- **Employer data:** company name, economic activity, phone, legal name, full address and
  references.
- **Employer person type** (física / moral) — used by the conciliation portal form.
- **Employment data:** position, **monthly salary**, pay period (daily/weekly/biweekly/
  monthly), weekly hours, work shift (diurna/nocturna/mixta), hire date, termination date.
- **Marketing/source:** how the client heard about the firm (Facebook, Google,
  recommendation, WhatsApp, TikTok, TV/radio, flyer…).
- **Office assignment** (Plaza Patria, Otay, CLT).
- **Free consultation tracking:** whether the free weekly consultation was offered,
  scheduled, and on which date.
- Indexed for fast lookups by CURP, name, and consultation date.

### 3.2 Case files (`Expediente`)

- **Automatic numbering** `AAAA-####` (year + sequential), unique and non-editable.
- Assigned to one **asesor** (legal advisor).
- **Amounts:** claimed amount (`monto_reclamado`) and settlement amount (`monto_convenio`).
- **Hearing scheduling** with date/time and recorded result.
- **Conciliation data:** dismissal type (justified/unjustified/voluntary/rescission/other),
  claimed benefits, **folio** and processing date.
- **Follow-up:** next action date, internal notes, priority (baja/media/alta).
- **Per-case WhatsApp automation toggle** (`notificar_whatsapp_auto`).

#### State machine with validated transitions

```
nuevo → solicitud → citatorio → audiencia → no_notificado ─┐
                                        ├→ reprogramacion ─┤
                                        ├→ convenio ───────┤
                                        ├→ sin_conciliacion─┼→ demanda → audiencia/convenio/cerrado
                                        └→ cerrado (from any state)
```

The model **rejects illegal transitions** (e.g. jumping from `nuevo` to `audiencia`) with
a clear message listing the allowed transitions. States have associated colors for UI badges.

### 3.3 Documents (`Documento`)

- Upload PDFs/images per case with type classification (INE, contract, evidence,
  screenshot, citatorio, PDF, other) and description; uploader and date recorded.
- Organized by year/month folders on disk.

### 3.4 Notes & Activity history

- **Notas** — free-form notes per case with author and timestamp.
- **Movimientos** — automatic audit trail of every action: creation, state change,
  update, document upload, note added, hearing result (who, when, what changed).

### 3.5 Notifications (bell)

In-app notifications for the user: transfers, avisos, system messages, reminders.
Each notification can carry a link; mark single or **all as read**.

### 3.6 Transfer requests between advisors

When an asesor can't attend a hearing (schedule conflict, etc.):

- He requests a **transfer** of the case, optionally suggesting a destination asesor,
  with a mandatory reason.
- Administration reviews the request, optionally **reassigns** to another advisor, and
  approves or rejects with a comment.
- Statuses: pending → approved / rejected / cancelled. Notifications keep everyone informed.

### 3.7 Avisos (mandatory admin notices)

- Admin creates notices/pending items with title, content, priority, and **optional
  expiry date** (auto-hides after expiry).
- Shown on every advisor/admin dashboard; users can mark them as **read/understood**
  (tracked per user via M2M).

### 3.8 Global search & filtering

- **Global search** across cases, clients, folios, companies.
- Advanced filters on the case list; asesores only see their own cases.

### 3.9 Calendar

- **Hearing calendar** (`calendario`) aggregating all scheduled hearings.

### 3.10 Reports & exports

- **Excel export** of cases.
- **Admin reports** page (`reportes_admin`) — productivity, totals per advisor.
- **PDF per case** (`pdf_expediente`) generated with WeasyPrint.

---

## 4. Dashboards (per role)

| Dashboard | What it shows |
|-----------|---------------|
| **Asesor** | Personal KPIs, his cases by state, upcoming actions/hearings, pending tasks, avisos |
| **Abogada** | Attorney-oriented overview of the practice's cases and documents |
| **Admin** | All cases, productivity reports, total amounts, avisos, export actions |
| **Finanzas** | Financial KPIs (see Finance module) |
| **Superadmin** | Platform administration panel + permission matrix |

---

## 5. Legal Calculation Engine (Cálculo Laboral)

### 5.1 Configurable legal rules (`LegalConfig`)

All legal parameters are stored in the database and editable from the Django admin —
**no code changes needed when the law changes**:

- **UMA** daily value, general minimum wage, **northern border zone (ZLF) minimum wage**.
- **Aguinaldo** days (min. legal 15).
- **Vacation premium %** (min. 25%).
- **Seniority premium:** days per year (12) + salary cap type (2× UMA / 2× SM / 2× ZLF SM)
  and multiplier.
- **Constitutional severance days** (3 months = 90).
- Only one config can be *active* at a time; saving one deactivates the others.

### 5.2 Vacation table (LFT 2023 reform)

The system implements the current Mexican vacation table (year 1 → 12 days, +2 per year up
to 20, then +2 every 5 years), extrapolating beyond the table when needed.

### 5.3 Concepts calculated

| Concept | Article | Type |
|---------|---------|------|
| Aguinaldo proporcional | Art. 87 LFT | automatic |
| Vacaciones proporcionales | Art. 76 LFT | automatic |
| Prima vacacional | Art. 80 LFT | automatic |
| Prima de antigüedad (with cap flag) | Art. 162 LFT | automatic |
| Indemnización constitucional (90 days) | Art. 50 LFT | automatic |
| Indemnización 20 días por año | Art. 50-II LFT | automatic |
| Vacaciones vencidas (manual days) | Art. 76 LFT | semi-auto |
| Horas extras (manual hours) | Art. 66-68 LFT | semi-auto |
| Salarios devengados (manual amount) | Art. 48 LFT | manual |
| Días festivos (manual days) | Art. 75 LFT | semi-auto |

### 5.4 Per-case calculation (`CalculoLaboral`)

- One calculation per expediente, storing a **snapshot of inputs** for history.
- **Checkboxes** let the advisor choose which concepts to include (defaults sensible).
- **Manual override** for vacation days actually owed (when some years were already paid
  or enjoyed) — shown with an *override applied* flag.
- Shows daily wage, days worked, years of service, per-concept breakdown with legal
  references, applied-cap warnings, and **total**.
- **Auto-recalculation** when client/case data or legal rules change (`recalcular`).
- **Quick simulation** (`simulacion-rapida`) — instant estimate for a prospect without
  creating a case: enter salary + dates and get the full breakdown.

---

## 6. Legal Document Generation

### 6.1 Machotes (reusable HTML templates)

- Templates categorized as: **Demanda Laboral, Carta Finiquito, Convenio, Solicitud,
  Citatorio, Otro**; with jurisdiction (Federal / Estatal BC / Both), optional dismissal
  type, icon, active flag, and ordering.
- **Favorite** templates float to the top of the editor.
- Template body is HTML using **markers** like `{{ nombre }}`, `{{ empresa }}`, etc.

### 6.2 Marker injection engine (`marcadores.py`)

- ~40 markers with **real case data**: client, employer, case, dates (in Spanish,
  e.g. "1 de enero de 2024"), salary formatting, **and computed benefits**
  (aguinaldo, vacations, indemnity…) pulled automatically from the calculation engine.
- Missing data renders as visible placeholders (`[CURP]`, `[MONTO]`, …) instead of blank
  or crashing — so the user knows exactly what to fill in.
- **Completeness checker**: lists which fields are complete/incomplete per section
  (Cliente, Empleo, Empresa, Expediente) with **direct edit links** and a completeness
  percentage.

### 6.3 Document workflow

1. Choose a machote from the catalog (or from the case).
2. **Prepare** — see which data is missing, click through to fix it.
3. **Edit/preview** the rendered document in the browser.
4. **Generate/download** as PDF.
5. Optionally **save the edited document as a new machote** (team template library grows
   organically).

### 6.4 Import machotes from Word

- `.docx` files (e.g. a folder of existing demandas) are converted to HTML templates via
  the `importar_machotes` command or web import, preserving markers where possible.
- Template library is managed from the Django admin or the machotes UI.

### 6.5 Demanda Laboral generator (`demanda_generator.py`)

- Generates a **professional Mexican labor lawsuit document** (Word `.docx`) with all
  case data, integrated calculations, print/filing-ready formatting.
- A **step-by-step wizard** (`demanda_asistente`) guides through sections of the demanda;
  a **direct generator** produces the document in one click.
- Downloads as `.docx` for editing/signing.

---

## 7. Conciliation Automation (Portal de Baja California)

The system integrates with the official portal `app.conciliacionbc.gob.mx` in **two modes**.

### 7.1 Server-side automation (`conciliacion_automation.py` + Celery)

- Fills the real multi-step portal flow: privacy notice → industry → conflict date &
  object → worker (solicitante) → employer (citado) → description → submit.
- Runs **headless** (server) or **visible/debug** mode.
- Executed asynchronously via **Celery worker** (or threading fallback without Redis) so
  HTTP requests never time out.
- Live progress page (`conciliacion_procesando`) showing **screenshots of the browser**
  and elapsed time; retry support.
- On success: captures the **folio**, saves the **acuse PDF** into the case, marks
  TareaConciliacion as completed with full logs.
- Management command `enviar_solicitud_conciliacion` for batch/CLI sending.

### 7.2 Acuse parser (`acuse_parser.py`)

When an official acuse PDF is available (auto-downloaded or manually uploaded), the
system **extracts its text with PyMuPDF** and auto-populates the case:

- Folio (e.g. `TIJ/26427/2026`), request date, applicant name, cited company, conflict
  date, object, conciliation unit.
- **Maps the conciliation object → dismissal type** (e.g. "Despido" → injustificado).
- **Preview screen** shows detected values vs. current values (new/differing flagged)
  and lets the advisor **confirm** before saving.

### 7.3 Chrome extension — "Conciliación BC Asistente"

For when automated navigation is detected or a CAPTCHA must be solved by a human, the
companion **Chrome extension (Manifest V3)** fills the portal form **in the advisor's own
browser**:

- The advisor clicks *Enviar a Conciliación → Desde mi navegador (Extensión de Chrome)*.
- The extension shows pending tasks (case number, client, company, CURP) in its popup.
- **🚀 Llenar en el portal** opens the portal with the form **already filled**
  (privacy, industry, dates, worker, employer, description) via a content script —
  so the portal sees a human-driven session.
- The advisor reviews, solves CAPTCHAs live, and clicks *Enviar solicitud* himself.
- **🔍 Ya envié, detectar acuse** — the extension detects the folio, downloads the acuse
  PDF, takes a screenshot, and **reports everything back to the app's API**
  (authenticated with the user's personal token), attaching the PDF to the case.
- Config screen (options) stores the app URL + token and verifies connectivity.
- The extension package can be **downloaded as a .zip** from the app
  (`/extension/descargar/`), ready to load unpacked into Chrome.

### 7.4 Manual fallbacks

- Upload the acuse PDF manually (`subir-conciliacion`), then preview/confirm the parsed data.
- Download a **pre-filled conciliation request PDF** to file manually at the center.
- Upload the acuse via the normal document flow.

---

## 8. WhatsApp Integration

Two delivery methods:

1. **Deep links (wa.me)** — free; opens WhatsApp with a pre-filled message.
2. **Twilio WhatsApp API** — server-sent messages (needs Twilio credentials); falls back
   to deep link automatically when not configured.

### Features

- **Templates** for: hearing reminder, citatorio, convenio follow-up, general follow-up,
  document request, custom messages — with variables (`{cliente}`, `{fecha}`, `{asesor}`…).
- **Automatic messages on state changes**: every case state has a configured message
  (new case, solicitud created, citatorio, hearing, not notified, rescheduled, convenio,
  no agreement, demanda, closed). Per-case toggle to enable/disable.
- **Message history** per case with status (pending/sent/failed), channel, and logs.
- Mexican phone normalization (adds country code 52, strips common formatting).
- Management command `enviar_whatsapp_automatico` to flush pending messages (with
  `--dry-run` and `--send-twilio` options).

---

## 9. Imports & Utilities

### 9.1 CLT import (citas from Excel)

`CLT.xlsx` (pre-scheduled conciliation appointments from the CCL) is imported as
**expedientes with scheduled hearings**:

- Per-sheet import (e.g. monthly tabs), auto-creates **advisor users** found in the file
  if needed, and cleanup options for test data.
- CURP is optional at import time and captured later (so numbers flow in fast).

### 9.2 Company catalog (`Empresa`)

- Import from `Empresas y Domicilios.xlsx` — **idempotent**, names normalized
  (uppercase, no accents, compacted spaces) so re-importing a growing file never duplicates.
- Person type auto-detected; detailed address kept for **autocomplete in the client form**
  (`empresas/buscar/` AJAX endpoint).

### 9.3 CURP generator

Standalone tool to **generate a valid CURP** from personal data (name, birth date,
gender, state) — saves manual lookups when onboarding clients.

### 9.4 User settings (Ajustes)

Per-user settings page: profile info, phone, WhatsApp automation preference, API token
management, extension configuration.

---

## 10. Finance Module (Módulo Finanzas)

Organized by **office** (sucursal) and by **work week** for operational reporting.

### 10.1 Offices

Catalog of firm offices with address, phone, manager, active flag. Each office has its
own income/expense/cash-register operations.

### 10.2 Work weeks

The finance system revolves around **weeks** (Mon–Sun): the current week is created
automatically; every movement can be attributed to a week. Weeks can be opened/closed.
Totals per week: **income** (cash + settlement payments), **expenses** (cash + expenses +
payroll) and **balance** are computed on the fly.

### 10.3 Settlement payments (`SettlementPayment`)

Payments received from settlement agreements (convenios): date, client, case, amount,
payment method (cash/transfer/check/credit/debit/deposit/other), office, notes, auditor.

### 10.4 Expenses (`Expense`)

Operational expenses per office with category (rent, utilities, internet, stationery,
advertising, salaries, gas, maintenance, taxes, equipment, furniture, insurance,
professional fees, other), provider, tax folio/invoice, and auditor.

### 10.5 Agreements & honorarios (`Agreement` / `Honorario`)

- **Convenios** with the client: amount, state (pending signature → signed → paid /
  partially paid / cancelled), responsible person, office, and automatic **total fees**.
- **Honorarios:** one or more fee entries per convenio with a **% tariff** (25/30/35/40/50%);
  amount auto-computed (`convenio × % ÷ 100`), expected/payment dates, paid/pending sums
  aggregated on the convenio.

### 10.6 Commissions (`Commission`)

Advisor commissions on closed convenios: % configurable, **amount auto-computed**,
state (pending/paid/cancelled), payment date, office, auditor.

### 10.7 Employees & payroll (`Employee` / `Payroll`)

- Employee catalog with position (administrative, legal advisor, supervisor, accountant,
  receptionist, assistant, director…), pay period, salary, office, active flag.
- **Payroll payments** per period: period type (weekly/biweekly/monthly/extraordinary/
  aguinaldo/vacation premium/bonus), period range, salary paid, deductions (ISR/IMSS),
  **total auto-computed** (`salario − descuentos`), office, auditor.

### 10.8 Cash register (`CashMovement`)

Daily cash movements per office and date: **income** (convenio payment, client payment,
advance, refund, other) or **expense** (stationery, gas, rent, utilities, internet,
phone, travel, commissions, fees, other). Category coherence with type is **validated**
(e.g. an income can't have an expense category). Reference field links to case/invoice.

### 10.9 Partners, loans & profit distribution

- **Partners (`Partner`):** participation % per partner for profit sharing.
- **Partner loans (`PartnerLoan`):** formal record of loans between partners (origin →
  destination, amount, concept, status, pending balance), replacing informal IOUs.
- **Profit distribution (`ProfitDistribution` + `PartnerProfit`):**
  - Auto-computes **net profit** = convenio amount − fees − commissions − withholdings −
    related expenses.
  - Distributes it among partners per their participation % (**individual share
    auto-calculated**), with states (draft → distributed → confirmed/cancelled).
  - Per-partner **accumulated summaries** (generated / paid / pending) auto-updated when
    distributions are confirmed.

### 10.10 Financial dashboard

- KPIs per office and overall; **monthly cash flow** chart fed by the `api_flujo_mensual`
  JSON endpoint; **Excel export** of the dashboard totals.
- **Convenio reports** (`reporte_convenios`) with Excel export.

---

## 11. Management Commands (CLI)

| Command | Purpose |
|---------|---------|
| `crear_usuarios_prueba` | Create test users (1 superadmin, 4 admins, 15 asesores) |
| `seed_datos` / `seed_clientes_prueba` | Seed demo cases (10 labor scenarios / full clients with calculations) |
| `enviar_recordatorios` | Send upcoming-action/hearing reminders (`--days`, `--dry-run`) |
| `enviar_solicitud_conciliacion` | Submit conciliation requests to the BC portal from CLI (`--headless`) |
| `enviar_whatsapp_automatico` | Flush pending automatic WhatsApp messages (`--dry-run`, `--send-twilio`) |
| `importar_clt` | Import CLT.xlsx citas as expedientes with hearings |
| `importar_empresas` | Import the companies/addresses catalog (idempotent) |
| `importar_machotes` | Convert `.docx` templates into machotes (`--reload`, `--file`) |
| `migrate_sqlite_to_pg` | One-shot data migration from SQLite to PostgreSQL |

---

## 12. Integrations Summary

| Service | Use | Config |
|---------|-----|--------|
| **Selenium** | Portal automation (headless/debug) | included |
| **Celery + Redis** | Background tasks (conciliation automation); threading fallback | `REDIS_URL` |
| **Twilio** | WhatsApp API sending (optional) | `TWILIO_*` env vars |
| **SMTP** | Password-reset emails (console backend in dev) | `EMAIL_*` env vars |
| **WeasyPrint** | PDF generation (expediente PDFs, documents) | included |
| **python-docx** | Word (.docx) demanda generation | included |
| **PyMuPDF (fitz)** | Acuse PDF text extraction | included |
| **openpyxl** | Excel imports (CLT, companies) and exports | included |
| **Chrome extension API** | Token-authenticated REST endpoints for the extension | personal `api_token` |
| **Railway** | Deployment; auto-detects domain, PostgreSQL and Redis env vars | env-driven |

---

## 13. Architecture & Tech Notes

- **Backend:** Django 5.x, `es-mx` locale, `America/Mexico_City` timezone.
- **Database:** SQLite (dev) / PostgreSQL (prod) via `DATABASE_URL`; Railway env
  auto-detection (`PGHOST`…).
- **Frontend:** Tailwind CSS (CDN) + **HTMX** for dynamic interactions (no heavy JS
  framework); responsive design.
- **Static files:** Whitenoise (`CompressedManifestStaticFilesStorage`) for zero-Nginx
  production serving.
- **Background work:** Celery when Redis is present, **threading fallback** otherwise
  (graceful degradation for local dev).
- **Auditability:** every key entity (payments, expenses, payroll, cash, loans,
  distributions, commissions) records `registrado_por`/`creado_por`.
- **Deployment:** Dockerfile, Railway config, entrypoint (auto-starts Celery worker when
  Redis exists), Nginx + Gunicorn recipe for VPS (droplet), and client-facing deploy guide.

---

## 14. Testing

The suite includes **48 tests** (expedientes, finanzas, automation) covering state
transition validation, financial calculations, and the verification script
`verify_demandas_calculos.py` (used by CI). Run with:

```bash
uv run python manage.py test
```

---

## 15. Quick Start (dev)

```bash
uv sync                          # install dependencies
uv run python manage.py migrate  # DB migrations
uv run python manage.py crear_usuarios_prueba
uv run python manage.py runserver
```

Test logins: `superadmin/Admin123!` · `admin1/Admin1!` · `asesor1/Asesor1!`
