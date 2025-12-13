# TravelPay Demo Docs Extractor

This repository automatically extracts and publishes a stable, machine-readable snapshot of key documentation sections from:

- https://payuat.travelpay.com.au/demo/

It is designed to run on a weekly GitHub Actions schedule and keep the latest extracted docs committed in the repo.

## What gets extracted

Only these four sections are captured:

- Code Sample
- Input Parameters
- Return Parameters
- Error Codes

## Why there are multiple outputs

The source page contains complex, multi-line table cells (especially `fingerprint`), which makes “direct-to-Markdown” unreliable.

So the pipeline is:

1. **Raw extraction JSON** (faithful snapshot of the HTML section content)
2. **Processed/normalized JSON** (Markdown-safe + curated where needed)
3. **Markdown** generated *only from the processed JSON*
4. **OpenAPI 3.1 spec** generated *only from the processed JSON* (schema container for JS tooling)

## Repository outputs

Generated files live under `docs/`:

- `docs/travelpay_demo.raw.json`  
  Unmodified extraction snapshot (closest representation of the page content).

- `docs/travelpay_demo.json`  
  Processed/normalized JSON intended to be stable for downstream tooling and Markdown generation.  
  This is the canonical input for schema generation.

- `docs/travelpay_demo.md`  
  Human-readable Markdown generated from `docs/travelpay_demo.json`.

- `docs/openapi.plugin.yaml`  
  OpenAPI 3.1 “schema container” generated from `docs/travelpay_demo.json`.  
  This is **not** a REST API spec; it exists so OpenAPI-capable tools can consume plugin schemas.

## Scripts

### 1) Extract + normalize + generate Markdown

`scrape_docs.py`

Runs the full extract pipeline and writes raw JSON, processed JSON, and Markdown.

Example:

```bash
python scrape_docs.py \
  --out-dir docs \
  --raw-json-name travelpay_demo.raw.json \
  --json-name travelpay_demo.json \
  --md-name travelpay_demo.md
````

### 2) Convert processed JSON to OpenAPI 3.1

`scripts/covert.py`

Reads the processed JSON and emits an OpenAPI 3.1 spec.

Example:

```bash
python scripts/covert.py \
  --in  docs/travelpay_demo.json \
  --out docs/openapi.plugin.yaml
```

If you want JSON output:

```bash
python scripts/covert.py \
  --in  docs/travelpay_demo.json \
  --out docs/openapi.plugin.json
```

## OpenAPI output notes

The generated OpenAPI file intentionally has:

* `servers: []`
* `paths: {}`

All useful material is under `components.schemas`, including:

* `ZpPaymentInitOptions` (input parameters for `$.zpPayment(options)`)
* `ZpPaymentResultMode0or2` (return payload for mode 0/2)
* `ZpPaymentResultMode1` (return payload for mode 1)
* `ZpPaymentErrorCode` (error codes, including wildcard families like `E02-*`)

It also includes `x-javascript-plugin` metadata with assets and a code sample.

## GitHub Actions automation

Workflow file:

* `.github/workflows/update-travelpay-demo.yml`

What it does:

1. Checks out the repo
2. Installs Python deps (`requests`, `beautifulsoup4`)
3. Runs `scrape_docs.py` to produce docs outputs
4. Runs `scripts/covert.py` to produce `docs/openapi.plugin.yaml`
5. Commits and pushes changes if anything under `docs/` changed (including new files)

The workflow runs:

* Weekly (cron)
* Manually (workflow_dispatch)

## Local development

Requirements:

* Python 3.11+
* pip packages:

  * `requests`
  * `beautifulsoup4`

Install:

```bash
pip install requests beautifulsoup4
```

Run the pipeline:

```bash
python scrape_docs.py --out-dir docs --raw-json-name travelpay_demo.raw.json --json-name travelpay_demo.json --md-name travelpay_demo.md
python scripts/covert.py --in docs/travelpay_demo.json --out docs/openapi.plugin.yaml
```
```
```
