# AI BOQ Reader (Odoo 19)

Upload an architectural or engineering drawing (PDF / PNG / JPG) and let a
vision-capable LLM extract a Bill of Quantities (BOQ) automatically. Edit, approve,
and convert to a Sales Order in a single workflow.

> **Odoo 19 build.** Uses `<list>` views, `res.groups.privilege`, `type='jsonrpc'`
> routes, the `aggregator=` ORM kwarg, `product_uom_id` on sale lines, and the
> `<t t-name="card">` kanban template. For Odoo 17/18 use the corresponding tag
> of this repository.

## Features

- Drag-and-drop drawing upload (single file or batch wizard)
- Multi-page PDF support (auto-rasterised at 200 DPI)
- Pluggable AI provider: **Anthropic Claude** (default), **OpenAI**, **Azure OpenAI**
- Strict-JSON extraction with per-line confidence scores (colour-coded in UI)
- Reusable BOQ templates
- **Pricelist cross-check** — re-prices AI lines against a chosen Odoo pricelist,
  with fuzzy product lookup by description for lines the AI didn't link to a product
- **Async analysis (optional)** — when OCA's `queue_job` is installed and enabled in
  Settings, `Analyse Design` dispatches to a worker so the UI returns immediately
- QWeb PDF report with company letterhead
- Optional Sales Order generation from approved BOQs
- REST endpoint at `POST /ai_boq/analyze` for external integrations
- Unit tests with mocked AI provider

## Installation

### 1. System dependencies

The PDF rasteriser needs `poppler`:

```bash
# Debian / Ubuntu
sudo apt install poppler-utils

# macOS
brew install poppler
```

### 2. Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Drop the module into your addons path

```bash
cp -r ai_boq_reader /path/to/odoo/addons/
./odoo-bin -u all -d <your_database>   # or just install via UI
```

### 4. Configure the AI provider

Go to **Settings → BOQ AI Reader** and set:

| Field            | Example                          |
|------------------|----------------------------------|
| Provider         | Anthropic Claude                 |
| Model ID         | `claude-sonnet-4-5`              |
| API Key          | `sk-ant-...`                     |

For Azure OpenAI, also set the endpoint URL.

## Usage

1. **BOQ AI → BOQ Projects → Create**
2. Set customer/project, upload the drawing, hit **Analyse Design**.
3. Wait for the AI to return (typically 10–40 s for 1–5 pages).
4. Review the extracted lines. Low-confidence rows are highlighted in red.
5. Adjust quantities/prices, then **Approve**.
6. Optionally **Create Sales Order** from the approved BOQ.

## Architecture

```
ai_boq_reader/
├── models/
│   ├── ai_service.py        # Provider-agnostic AI wrapper (Anthropic / OpenAI / Azure)
│   ├── boq_project.py       # Main project + workflow
│   ├── boq_line.py          # Line items with confidence band
│   ├── boq_template.py      # Reusable templates
│   └── res_config_settings.py
├── views/                   # form / tree / kanban / search / settings / menus
├── wizards/                 # bulk import wizard
├── reports/                 # QWeb PDF
├── controllers/main.py      # /ai_boq/analyze REST endpoint
├── security/                # groups, record rules, ACL CSV
└── tests/                   # mocked-AI unit tests
```

## Pricelist cross-check

Set a **Pricelist** on the BOQ form. After AI analysis the system runs an automatic
cross-check; you can also re-run it manually with the **Re-price from Pricelist** button.

Behaviour per line:

| AI line state | What happens |
|---|---|
| Linked to a `product.product` | Pricelist price for that product replaces the AI estimate |
| No product, description like "Reinforcement Steel Y12" | Fuzzy lookup: tokens of length ≥4 must all appear in a product name. If exactly one product matches, it gets linked and re-priced. Ambiguous matches are left alone. |
| No product, vague description ("LS", "misc") | Untouched, kept in `unmatched` count |

The summary at the bottom of the **Pricing** tab shows direct/fuzzy/unmatched counts
and the five largest price corrections (in % terms).

## Async analysis with queue_job

Install the OCA `queue_job` module (`pip install odoo-addon-queue-job` or clone
[OCA/queue](https://github.com/OCA/queue)), then in **Settings → BOQ AI Reader**
enable *Run AI analysis asynchronously*.

When enabled, clicking **Analyse Design**:

1. Sets the BOQ to `analyzing`
2. Dispatches `_run_analysis` to the `root.ai_boq` channel
3. Stores the job UUID on the record (visible on the form)
4. Returns control to the user immediately

Configure a worker in your `odoo.conf`:

```ini
workers = 4
[queue_job]
channels = root:1,root.ai_boq:2
```

If `queue_job` is not installed or the toggle is off, analysis runs inline
(synchronously) — the toggle is safe to enable preemptively.

## Extending

### Use a different AI provider

Subclass `ai.boq.service` and override `_call_provider`. Set
`ai_boq.provider` to your custom key.

### Custom UoM mapping

Edit `BoqProject._resolve_uom` to map AI-supplied units to your installed
`uom.uom` records (the default mapping is intentionally conservative since
Odoo's stock UoMs vary by install).

### Async analysis with queue_job

If `queue_job` is installed in your stack, decorate `action_analyze` with
`@job` to push analysis to a worker queue.

## Running tests

```bash
./odoo-bin -d <db> -i ai_boq_reader --test-enable --stop-after-init
```

## Licence

LGPL-3
