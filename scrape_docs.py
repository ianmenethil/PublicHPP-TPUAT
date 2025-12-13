#!/usr/bin/env python3
"""
Extract 4 documentation sections from https://payuat.travelpay.com.au/demo/:

- Code Sample
- Input Parameters
- Return Parameters
- Error Codes

Outputs (default):
- docs/travelpay_demo.raw.json   (raw extraction snapshot)
- docs/travelpay_demo.json       (normalized + curated + markdown-safe)
- docs/travelpay_demo.md         (generated strictly from normalized JSON)

Key design choices:
- Markdown is generated from the normalized JSON only (never directly from HTML).
  This prevents repeat breakage when values contain Markdown-special characters.
- We keep Input/Return sections as bullet lists (not tables) because many cells are
  multiline and become unreadable in Markdown tables. If you want tables later, add
  an alternate renderer, but keep JSON as the source of truth.

Curation:
- The raw HTML content sometimes mixes versions (v3/v4/v5) in a single "fingerprint"
  remark block. For the normalized JSON + Markdown, we keep only v5 (SHA3-512) guidance.
  Raw JSON remains unmodified.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup, Tag


TARGET_URL = "https://payuat.travelpay.com.au/demo/"
SECTION_TITLES = ["Code Sample", "Input Parameters", "Return Parameters", "Error Codes"]


# ----------------------------
# Fetch + core text utilities
# ----------------------------

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip()).lower()


def _clean_code(s: str) -> str:
    """Preserve indentation; normalize newlines; strip outer blank lines; trim trailing spaces per line."""
    s = (s or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in s.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def _normalize_cell_artifacts(text: str) -> str:
    """
    Fix formatting artifacts observed on this page while preserving meaningful newlines.
    """
    t = (text or "").replace("\r\n", "\n").replace("\r", "\n")

    # "( newline | newline )" -> "(|)"
    t = re.sub(r"\(\s*\n\s*\|\s*\n\s*\)", "(|)", t)

    # "token \n : value" -> "token: value"
    t = re.sub(r"\n\s*:\s*", ": ", t)

    # "token: : value" -> "token: value"
    t = re.sub(r":\s*:\s*", ": ", t)

    # Remove spurious standalone "*" lines
    lines: List[str] = []
    for ln in t.splitlines():
        if ln.strip() in {"*", "•"}:
            continue
        lines.append(ln)
    t = "\n".join(lines)

    # Normalize whitespace around newlines; keep newlines
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n[ \t]+", "\n", t)
    t = re.sub(r"[ \t]{2,}", " ", t)

    # Collapse excessive blank lines
    t = re.sub(r"\n{3,}", "\n\n", t)

    return t.strip()


def _clean_prose(text: str) -> str:
    """Flatten to a single line of prose (used for notes, labels)."""
    t = _normalize_cell_artifacts(text)
    return re.sub(r"\s+", " ", t).strip()


def _cell_text(cell: Tag) -> str:
    """Extract table cell text with <br> preserved as newlines, then normalize."""
    raw = cell.get_text(separator="\n", strip=True)
    return _normalize_cell_artifacts(raw)


def _fetch_html(url: str, *, timeout: int = 30, retries: int = 3, backoff_s: float = 1.0) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (doc-extractor; GitHub Actions)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    last_err: Optional[Exception] = None
    for i in range(retries):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            last_err = e
            if i < retries - 1:
                time.sleep(backoff_s * (2 ** i))
    raise RuntimeError(f"Failed to fetch {url}: {last_err}")


def _sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="replace")).hexdigest()


# ----------------------------
# HTML section location + tables
# ----------------------------

def _find_panel_body(soup: BeautifulSoup, title: str) -> Optional[Tag]:
    title_n = _norm(title)
    for heading in soup.select("div.panel-heading"):
        if _norm(heading.get_text(strip=True)) == title_n:
            panel = heading.find_parent(
                lambda t: isinstance(t, Tag)
                and t.has_attr("class")
                and any("panel" in c for c in t["class"])
            )
            if panel:
                return panel.select_one("div.panel-body")
    return None


def _table_to_rows(table: Tag) -> Tuple[List[str], List[Dict[str, str]]]:
    headers: List[str] = []
    thead = table.find("thead")
    if thead:
        headers = [th.get_text(strip=True) for th in thead.find_all(["th", "td"])]
    if not headers:
        first_tr = table.find("tr")
        if first_tr:
            headers = [th.get_text(strip=True) for th in first_tr.find_all(["th", "td"])]

    headers = [h if h else f"col_{i}" for i, h in enumerate(headers)]
    rows: List[Dict[str, str]] = []

    body_rows = table.select("tbody tr") or table.find_all("tr")[1:]
    for tr in body_rows:
        tds = tr.find_all("td")
        if not tds:
            continue
        row: Dict[str, str] = {}
        for i, h in enumerate(headers):
            row[h] = _cell_text(tds[i]) if i < len(tds) else ""
        rows.append(row)

    return headers, rows


def _nearest_label_for_table(panel_body: Tag, table: Tag) -> str:
    elems: List[Tag] = [e for e in panel_body.find_all(True)]
    try:
        idx = elems.index(table)
    except ValueError:
        return ""

    for j in range(idx - 1, -1, -1):
        e = elems[j]
        if e.name == "p":
            txt = _clean_prose(e.get_text(separator=" ", strip=True))
            if not txt:
                continue
            if "mode" in txt.lower() or "returned" in txt.lower():
                return txt
    return ""


# ----------------------------
# Section extractors
# ----------------------------

def _strip_embedded_js_sample(paragraph_text: str) -> str:
    if not paragraph_text:
        return ""
    t = paragraph_text.replace("\r\n", "\n").replace("\r", "\n")

    # remove from "var payment" through "payment.init();"
    t = re.sub(
        r"\bvar\s+payment\b.*?\bvar\s+result\s*=\s*payment\.init\(\)\s*;\s*",
        "",
        t,
        flags=re.IGNORECASE | re.DOTALL,
    )
    t = re.sub(r"\bvar\s+payment\b.*$", "", t, flags=re.IGNORECASE | re.DOTALL)
    return _clean_prose(t)


def _extract_code_sample(panel_body: Tag) -> Dict[str, Any]:
    stylesheet_href: Optional[str] = None
    javascript_href: Optional[str] = None
    stylesheet_display: Optional[str] = None
    javascript_display: Optional[str] = None

    for p in panel_body.find_all("p"):
        txt = _norm(p.get_text(" ", strip=True))
        if "stylesheet:" in txt:
            a = p.find("a")
            if a:
                stylesheet_href = a.get("href")
                stylesheet_display = _clean_prose(a.get_text(" ", strip=True))
        if "javascript:" in txt:
            for a in p.find_all("a"):
                href = (a.get("href") or "")
                if href.lower().endswith(".js"):
                    javascript_href = href
                    javascript_display = _clean_prose(a.get_text(" ", strip=True))
                elif href.lower().endswith(".css") and not stylesheet_href:
                    stylesheet_href = href
                    stylesheet_display = _clean_prose(a.get_text(" ", strip=True))

    code_blocks: List[str] = []
    for pre in panel_body.find_all("pre"):
        code_blocks.append(_clean_code(pre.get_text()))
    code = "\n\n".join([c for c in code_blocks if c])

    notes: List[str] = []
    for p in panel_body.find_all("p"):
        raw = p.get_text(separator="\n", strip=True)
        if not raw:
            continue
        low = raw.lower()
        if "stylesheet:" in low or "javascript:" in low:
            continue
        cleaned = _strip_embedded_js_sample(raw)
        if cleaned:
            notes.append(cleaned)

    deduped: List[str] = []
    seen = set()
    for n in notes:
        key = _norm(n)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(n)

    return {
        "heading": "Code Sample",
        "assets": {
            "stylesheet": {"href": stylesheet_href, "display": stylesheet_display},
            "javascript": {"href": javascript_href, "display": javascript_display},
        },
        "code": code,
        "notes": deduped,
    }


def _extract_single_table_section(panel_body: Tag, heading: str) -> Dict[str, Any]:
    table = panel_body.find("table")
    if not table:
        return {"heading": heading, "headers": [], "rows": []}
    headers, rows = _table_to_rows(table)
    return {"heading": heading, "headers": headers, "rows": rows}


def _extract_return_parameters(panel_body: Tag) -> Dict[str, Any]:
    tables = panel_body.find_all("table")
    out_tables: List[Dict[str, Any]] = []
    for i, t in enumerate(tables):
        headers, rows = _table_to_rows(t)
        label = _nearest_label_for_table(panel_body, t)
        out_tables.append({"index": i, "label": label, "headers": headers, "rows": rows})
    return {"heading": "Return Parameters", "tables": out_tables}


# ----------------------------
# Raw JSON extraction
# ----------------------------

def extract_raw(url: str, html_path: Optional[Path] = None) -> Tuple[Dict[str, Any], str]:
    if html_path:
        html = html_path.read_text(encoding="utf-8", errors="replace")
    else:
        html = _fetch_html(url)
    html_hash = _sha256_text(html)

    soup = BeautifulSoup(html, "html.parser")
    bodies = {title: _find_panel_body(soup, title) for title in SECTION_TITLES}

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    doc = {
        "metadata": {
            "url": url,
            "extracted_at": now,
            "sections": SECTION_TITLES,
            "html_sha256": html_hash,
        },
        "sections": {
            "code_sample": _extract_code_sample(bodies["Code Sample"]) if bodies["Code Sample"] else {
                "heading": "Code Sample",
                "assets": {"stylesheet": {"href": None, "display": None}, "javascript": {"href": None, "display": None}},
                "code": "",
                "notes": [],
            },
            "input_parameters": _extract_single_table_section(bodies["Input Parameters"], "Input Parameters") if bodies["Input Parameters"] else {
                "heading": "Input Parameters",
                "headers": [],
                "rows": [],
            },
            "return_parameters": _extract_return_parameters(bodies["Return Parameters"]) if bodies["Return Parameters"] else {
                "heading": "Return Parameters",
                "tables": [],
            },
            "error_codes": _extract_single_table_section(bodies["Error Codes"], "Error Codes") if bodies["Error Codes"] else {
                "heading": "Error Codes",
                "headers": [],
                "rows": [],
            },
        },
    }
    return doc, html_hash


# ----------------------------
# Normalization + curation (md-safe JSON)
# ----------------------------

def _md_escape_for_bold(s: str) -> str:
    """
    Escape characters that can break **bold** markdown when they appear in the key itself.
    """
    s = (s or "")
    s = s.replace("\\", "\\\\")
    s = s.replace("*", "\\*")
    s = s.replace("_", "\\_")
    return s


def _curate_fingerprint_v5() -> str:
    """
    Curated v5-only fingerprint guidance. Returned as a multiline block suitable for Markdown bullets.
    """
    lines = [
        "Fingerprint (v5) is a SHA3-512 hash of the following pipe-delimited string:",
        "`apiKey|userName|password|mode|paymentAmount|merchantUniquePaymentId|timestamp`",
        "Credentials provided by Zenith Payments are case sensitive.",
        "Field notes:",
        "`apiKey`: refer apiKey parameter",
        "`userName`: provided by Zenith Payments",
        "`password`: provided by Zenith Payments",
        "`mode`: refer mode parameter",
        "`paymentAmount`: amount in cents without symbol (e.g. $150.53 => 15053). Pass 0 when mode is 2.",
        "`merchantUniquePaymentId`: refer merchantUniquePaymentId parameter",
        "`timestamp`: current datetime in UTC ISO 8601 format (yyyy-MM-ddTHH:mm:ss).",
    ]
    return "\n".join(lines)


def normalize_doc(raw_doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Produce a second JSON document:
    - adds md_* fields for safe Markdown rendering
    - applies targeted curation to the normalized JSON (raw JSON remains unchanged)
    """
    doc = copy.deepcopy(raw_doc)
    doc.setdefault("metadata", {})
    doc["metadata"]["normalized_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    doc["metadata"]["normalized_from_html_sha256"] = raw_doc.get("metadata", {}).get("html_sha256")

    sections = doc.get("sections", {})

    inp = sections.get("input_parameters", {})
    for r in inp.get("rows", []) or []:
        field = (r.get("Field Name") or r.get("Field") or "").strip()
        if field:
            r["md_field"] = _md_escape_for_bold(field)

        # v5-only curation for fingerprint in processed JSON
        if field.lower() == "fingerprint":
            r["Remarks"] = _curate_fingerprint_v5()
            r["curated"] = True
            r["curation_note"] = "Kept v5 (SHA3-512) only; removed v4/v3 references."

    ret = sections.get("return_parameters", {})
    for t in ret.get("tables", []) or []:
        for r in t.get("rows", []) or []:
            param = (r.get("Parameter") or "").strip()
            if param:
                r["md_parameter"] = _md_escape_for_bold(param)

    err = sections.get("error_codes", {})
    for r in err.get("rows", []) or []:
        code = (r.get("Error Code") or "").strip()
        if code:
            r["md_error_code"] = _md_escape_for_bold(code)

    return doc


# ----------------------------
# Markdown generation (from normalized JSON only)
# ----------------------------

def _md_inline_code(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return "``"
    s = s.replace("`", "\\`")
    return f"`{s}`"


def _emit_key_value_bullets(
    rows: List[Dict[str, str]],
    key_field: str,
    val_field: str,
    md_key_field: Optional[str] = None,
) -> str:
    out: List[str] = []
    for r in rows:
        k_raw = (r.get(key_field, "") or "").strip()
        if not k_raw:
            continue
        k_md = (r.get(md_key_field, "") or "").strip() if md_key_field else ""
        if not k_md:
            k_md = _md_escape_for_bold(k_raw)

        v = (r.get(val_field, "") or "").strip()
        if not v:
            out.append(f"- **{k_md}**")
            continue

        lines = [ln.strip() for ln in v.splitlines() if ln.strip()]
        if len(lines) <= 1:
            out.append(f"- **{k_md}** — {lines[0] if lines else v.strip()}")
        else:
            out.append(f"- **{k_md}**")
            for ln in lines:
                out.append(f"  - {ln}")

    return "\n".join(out) + ("\n" if out else "")


def _emit_input_parameter_bullets(rows: List[Dict[str, str]]) -> str:
    out: List[str] = []
    for r in rows:
        field = (r.get("Field Name") or r.get("Field") or "").strip()
        if not field:
            continue
        field_md = (r.get("md_field") or "").strip() or _md_escape_for_bold(field)

        dtype = re.sub(r"\s+", " ", (r.get("Data Type") or "").strip())
        cond = re.sub(r"\s+", " ", (r.get("Conditional") or "").strip())
        meta_parts = [p for p in [dtype, cond] if p]
        meta = f" ({', '.join(meta_parts)})" if meta_parts else ""

        remarks = (r.get("Remarks") or "").strip()
        rem_lines = [ln.strip() for ln in remarks.splitlines() if ln.strip()]

        if not rem_lines:
            out.append(f"- **{field_md}**{meta}")
        elif len(rem_lines) == 1:
            out.append(f"- **{field_md}**{meta} — {rem_lines[0]}")
        else:
            out.append(f"- **{field_md}**{meta}")
            for ln in rem_lines:
                out.append(f"  - {ln}")

    return "\n".join(out) + ("\n" if out else "")


def to_markdown_from_normalized(doc: Dict[str, Any]) -> str:
    md: List[str] = []
    md.append("# TravelPay Demo Extract\n\n")
    md.append(f"- Source: {_md_inline_code(doc.get('metadata', {}).get('url', ''))}\n")
    md.append(f"- Extracted (UTC): {_md_inline_code(doc.get('metadata', {}).get('extracted_at', ''))}\n")
    if doc.get("metadata", {}).get("html_sha256"):
        md.append(f"- HTML SHA256: {_md_inline_code(doc['metadata']['html_sha256'])}\n")
    md.append("\n")

    sections = doc.get("sections", {})

    cs = sections.get("code_sample", {})
    md.append("## Code Sample\n\n")
    assets = cs.get("assets", {}) or {}
    ss = assets.get("stylesheet", {}) or {}
    js = assets.get("javascript", {}) or {}
    if ss.get("href") or ss.get("display"):
        md.append(f"- Stylesheet: {_md_inline_code(ss.get('display') or '')} ({ss.get('href') or ''})\n")
    if js.get("href") or js.get("display"):
        md.append(f"- Javascript: {_md_inline_code(js.get('display') or '')} ({js.get('href') or ''})\n")
    md.append("\n")
    if cs.get("code"):
        md.append("```js\n")
        md.append(_clean_code(cs["code"]) + "\n")
        md.append("```\n\n")
    if cs.get("notes"):
        md.append("Notes:\n")
        for n in cs["notes"]:
            md.append(f"- {n}\n")
        md.append("\n")

    inp = sections.get("input_parameters", {})
    md.append("## Input Parameters\n\n")
    md.append(_emit_input_parameter_bullets(inp.get("rows", []) or []) or "_No rows found._\n\n")
    if not (inp.get("rows") or []):
        md.append("\n")

    ret = sections.get("return_parameters", {})
    md.append("## Return Parameters\n\n")
    tables = ret.get("tables", []) or []
    if not tables:
        md.append("_No tables found._\n\n")
    else:
        for t in tables:
            label = (t.get("label") or "").strip() or f"Table {t.get('index')}"
            md.append(f"### {label}\n\n")
            rows = t.get("rows", []) or []
            md.append(_emit_key_value_bullets(rows, "Parameter", "Value", md_key_field="md_parameter") or "_No rows found._\n")
            md.append("\n")

    err = sections.get("error_codes", {})
    md.append("## Error Codes\n\n")
    rows = err.get("rows", []) or []
    md.append(_emit_key_value_bullets(rows, "Error Code", "Description", md_key_field="md_error_code") or "_No error code rows found._\n")
    md.append("\n")

    return "".join(md)


# ----------------------------
# Output writing
# ----------------------------

@dataclass
class Outputs:
    raw_json_path: Path
    normalized_json_path: Path
    md_path: Path


def write_outputs(
    raw_doc: Dict[str, Any],
    normalized_doc: Dict[str, Any],
    out_dir: Path,
    raw_json_name: str,
    json_name: str,
    md_name: str,
) -> Outputs:
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_json_path = out_dir / raw_json_name
    normalized_json_path = out_dir / json_name
    md_path = out_dir / md_name

    raw_json_path.write_text(json.dumps(raw_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    normalized_json_path.write_text(json.dumps(normalized_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(to_markdown_from_normalized(normalized_doc), encoding="utf-8")

    return Outputs(raw_json_path=raw_json_path, normalized_json_path=normalized_json_path, md_path=md_path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=TARGET_URL)
    ap.add_argument("--html-file", default=None, help="Use local HTML file instead of fetching")
    ap.add_argument("--out-dir", default="docs")
    ap.add_argument("--raw-json-name", default="travelpay_demo.raw.json")
    ap.add_argument("--json-name", default="travelpay_demo.json")
    ap.add_argument("--md-name", default="travelpay_demo.md")
    args = ap.parse_args()

    html_file = Path(args.html_file) if args.html_file else None

    raw_doc, _ = extract_raw(args.url, html_path=html_file)
    normalized_doc = normalize_doc(raw_doc)
    outputs = write_outputs(
        raw_doc,
        normalized_doc,
        Path(args.out_dir),
        args.raw_json_name,
        args.json_name,
        args.md_name,
    )

    print(f"Wrote: {outputs.raw_json_path}")
    print(f"Wrote: {outputs.normalized_json_path}")
    print(f"Wrote: {outputs.md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
