# Real Estate Factory — Data Flow, Retention & Privacy Architecture Note

## 1. Scope & System Topology
Real Estate Factory processes commercial property valuations, development agreements, title chain documents, and financial metrics across multi-tenant valuation firms and financial institutions.

```
┌─────────────────┐       HTTPS / TLS 1.3       ┌──────────────────────────────┐
│  Client Console │ ──────────────────────────> │  FastAPI Gateway (§5 Router) │
└─────────────────┘                             └──────────────┬───────────────┘
                                                               │
                                               ┌───────────────┴───────────────┐
                                               │ Postgres / PostGIS + Alembic  │
                                               │ (Encrypted At-Rest AES-256)   │
                                               └───────────────────────────────┘
```

---

## 2. Data Categories & Storage Locations

| Data Category | Primary Storage | Encryption | Retention Period | Access Scope |
|---|---|---|---|---|
| **User & Tenant Credentials** | PostgreSQL `users` table | Argon2id Hashing | Duration of contract + 30 days | Unscoped auth subsystem |
| **Mandates & Property Assets** | PostgreSQL `mandates`, `properties` | AES-256 at-rest | 8 years (IBBI statutory mandate) | Firm-Scoped (`FirmScope`) |
| **Property Documents (PDF/Images)** | AWS S3 / Encrypted Storage | Server-side AES-256 | 8 years | Firm-Scoped (`FirmScope`) |
| **Valuation Lines & Metrics** | PostgreSQL `valuation_lines` | AES-256 at-rest | 8 years | Firm-Scoped (`FirmScope`) |
| **Audit Logs & Telemetry** | PostgreSQL `audit_events` | AES-256 at-rest | 10 years (immutable append-only) | Admin / Valuer scoped |
| **PII & Location Privacy Data** | Redacted before log emission | PII Redaction Engine | Redacted instantly | Admin / Valuer only; stripped for `client` role |

---

## 3. Third-Party Data Processing

1. **LLM Inference Providers (Groq / Anthropic / Google Gemini)**:
   - **Data Transmitted**: De-identified property facts, market context, and structured prompt outline text.
   - **PII Exclusion**: Exact owner names and survey numbers are stripped via `redaction.py` prior to LLM submission. Zero model training retention under zero-data-retention enterprise SLAs.
2. **Document OCR Processors**:
   - **Data Transmitted**: Uploaded title deeds and floorplans processed inside sandboxed OCR workers.

---

## 4. Location & Confidentiality Privacy Controls

1. **Client-Role Coordinate & Owner Exclusion**:
   - API responses generated for `role="client"` are passed through `filter_client_role_response(...)`, which strips exact GPS coordinates (`latitude`, `longitude`, `coordinates`) and owner names (`owner`, `owner_details`), exposing only micro-market region data.
2. **XLSX Formula Injection Neutralization**:
   - User-supplied textual fields (tenant names, property addresses, descriptions) starting with `=`, `+`, `-`, `@` are prefixed with `'` (single quote) during openpyxl export, rendering them inert text in Excel.
3. **Firm Corpus Isolation**:
   - Past report corpus search is strictly isolated by `scope.firm_id`. Cross-firm retrieval attempts return empty results and emit an `AuditEvent` (`action="retrieval_cross_firm_attempt"`).
