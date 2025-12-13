#!/usr/bin/env python3
"""
Convert the processed TravelPay demo JSON into an OpenAPI 3.1 spec.

Important:
- This OpenAPI document is a *schema container* for a JavaScript plugin, NOT a REST API.
- servers: [] and paths: {} are intentionally empty.
- The output is primarily under components.schemas.

Input:
  --in  docs/travelpay_demo.json

Output:
  --out docs/openapi.plugin.yaml   (YAML)  OR
  --out docs/openapi.plugin.json   (JSON) if output filename ends with .json

No external dependencies.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------
# Minimal YAML emitter
# ---------------------------

_SAFE_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _yaml_quote(s: str) -> str:
    s = s.replace("'", "''")
    return "'" + s + "'"


def _yaml_key(k: str) -> str:
    return k if _SAFE_KEY_RE.match(k or "") else _yaml_quote(k)


def _yaml_scalar(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, str):
        if v == "":
            return "''"
        needs_quote = (
            v.strip() != v
            or any(ch in v for ch in [":", "#", "{", "}", "[", "]", ",", "&", "*", "!", "|", ">", "%", "@", "`"])
            or v.lower() in {"null", "true", "false", "yes", "no", "~"}
            or v.startswith(("-", "?", ":", " "))
        )
        return _yaml_quote(v) if needs_quote else v
    return _yaml_quote(str(v))


def yaml_dump(obj: Any, indent: int = 0) -> str:
    lines: List[str] = []

    def emit(o: Any, ind: int, key_prefix: Optional[str] = None) -> None:
        sp = " " * ind

        if isinstance(o, dict):
            if key_prefix is not None:
                lines.append(f"{sp}{key_prefix}:")
            for k, v in o.items():
                kk = _yaml_key(str(k))
                if isinstance(v, (dict, list)):
                    emit(v, ind, kk)
                elif isinstance(v, str) and "\n" in v:
                    lines.append(f"{sp}{kk}: |")
                    for ln in v.splitlines():
                        lines.append(f"{sp}  {ln}")
                else:
                    lines.append(f"{sp}{kk}: {_yaml_scalar(v)}")
            return

        if isinstance(o, list):
            if key_prefix is not None:
                lines.append(f"{sp}{key_prefix}:")
            for item in o:
                if isinstance(item, dict):
                    lines.append(f"{sp}-")
                    emit(item, ind + 2)
                elif isinstance(item, list):
                    lines.append(f"{sp}-")
                    emit(item, ind + 2)
                elif isinstance(item, str) and "\n" in item:
                    lines.append(f"{sp}- |")
                    for ln in item.splitlines():
                        lines.append(f"{sp}  {ln}")
                else:
                    lines.append(f"{sp}- {_yaml_scalar(item)}")
            return

        if key_prefix is not None:
            lines.append(f"{sp}{key_prefix}: {_yaml_scalar(o)}")
        else:
            lines.append(f"{sp}{_yaml_scalar(o)}")

    emit(obj, indent)
    return "\n".join(lines) + "\n"


# ---------------------------
# Helpers: type + enums
# ---------------------------

def _map_type(data_type: str) -> Tuple[str, Optional[str]]:
    t = (data_type or "").strip().lower()
    t = re.sub(r"\s+", " ", t)
    if "boolean" in t:
        return "boolean", None
    if t in {"int", "integer"}:
        return "integer", None
    if t in {"number", "float", "double", "decimal"}:
        return "number", None
    if t in {"function"}:
        return "string", None
    return "string", None


def _extract_enum_from_remarks(remarks: str) -> Optional[List[int]]:
    if not remarks:
        return None
    vals: List[int] = []
    for ln in remarks.splitlines():
        m = re.match(r"^\s*(\d+)\s*-\s+.+$", ln.strip())
        if m:
            vals.append(int(m.group(1)))
    return vals or None


def _extract_enum_from_value_map(value: str) -> Optional[List[int]]:
    if not value:
        return None
    vals: List[int] = []
    for ln in value.splitlines():
        m = re.match(r"^\s*(\d+)\s*=>\s*.+$", ln.strip())
        if m:
            vals.append(int(m.group(1)))
    return vals or None


def _guess_string_enum(value: str) -> Optional[List[str]]:
    if not value:
        return None
    low = value.lower()
    if "possible values" not in low and "possiible values" not in low:
        return None
    lines = [ln.strip() for ln in value.splitlines() if ln.strip()]
    while lines and ("possible values" in lines[0].lower() or "possiible values" in lines[0].lower()):
        lines.pop(0)
    lines = [ln for ln in lines if ln.lower() != "format:"]
    out: List[str] = []
    for ln in lines:
        if "=>" in ln:
            out.append(ln.split("=>", 1)[0].strip())
        else:
            out.append(ln)
    dedup: List[str] = []
    seen = set()
    for x in out:
        if not x or x in seen:
            continue
        seen.add(x)
        dedup.append(x)
    return dedup or None


def _iso_timestamp_schema() -> Dict[str, Any]:
    return {
        "type": "string",
        "description": "UTC ISO-8601 timestamp (yyyy-MM-ddTHH:mm:ss)",
        "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$",
        "examples": ["2025-12-13T09:56:03"],
    }


def _iso_date_schema() -> Dict[str, Any]:
    return {
        "type": "string",
        "description": "UTC ISO-8601 date (yyyy-MM-dd)",
        "pattern": r"^\d{4}-\d{2}-\d{2}$",
        "examples": ["2025-12-13"],
    }


# ---------------------------
# Build OpenAPI
# ---------------------------

def build_openapi(doc: Dict[str, Any]) -> Dict[str, Any]:
    meta = (doc.get("metadata") or {}) if isinstance(doc, dict) else {}
    sections = (doc.get("sections") or {}) if isinstance(doc, dict) else {}

    # Be tolerant: some older JSON formats might store code_sample as a string.
    cs = sections.get("code_sample")
    code_sample_text = ""
    stylesheet = None
    javascript = None

    if isinstance(cs, dict):
        code_sample_text = cs.get("code") or ""
        assets = cs.get("assets") or {}
        if isinstance(assets, dict):
            stylesheet = (assets.get("stylesheet") or {}).get("href") if isinstance(assets.get("stylesheet"), dict) else None
            javascript = (assets.get("javascript") or {}).get("href") if isinstance(assets.get("javascript"), dict) else None
    elif isinstance(cs, str):
        code_sample_text = cs

    extracted_at = meta.get("extracted_at") or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # ---- Input parameters -> init options schema
    input_rows = ((sections.get("input_parameters") or {}).get("rows") or []) if isinstance(sections.get("input_parameters"), dict) else []
    init_props: Dict[str, Any] = {}
    required: List[str] = []

    needs_customer_and_amount_if_mode_0_or_2 = False
    timestamp_alias_present = False

    for row in input_rows:
        if not isinstance(row, dict):
            continue
        name = (row.get("Field Name") or "").strip()
        if not name:
            continue

        dtype = row.get("Data Type") or "string"
        cond = (row.get("Conditional") or "").strip().lower()
        remarks = row.get("Remarks") or ""

        oatype, _ = _map_type(dtype)
        prop: Dict[str, Any] = {"type": oatype}
        if remarks:
            prop["description"] = remarks

        if name == "mode":
            prop["type"] = "integer"
            prop["enum"] = [0, 1, 2, 3]
        if name == "displayMode":
            prop["type"] = "integer"
            prop["enum"] = [0, 1]
        if name == "overrideFeePayer":
            prop["type"] = "integer"
            vals = _extract_enum_from_remarks(remarks)
            if vals:
                prop["enum"] = vals
        if name == "userMode":
            prop["type"] = "integer"
            vals = _extract_enum_from_remarks(remarks)
            if vals:
                prop["enum"] = vals

        if name in {"timestamp", "timeStamp"}:
            prop = _iso_timestamp_schema()
            if name == "timeStamp":
                prop["description"] = "Alias of `timestamp` (seen in code sample). Prefer `timestamp` where possible."
                timestamp_alias_present = True

        if name == "departureDate":
            prop = _iso_date_schema()

        if (row.get("Data Type") or "").strip().lower() == "function":
            prop["type"] = "string"
            prop["x-javascriptType"] = "function"

        if cond == "required":
            required.append(name)

        if "required if mode is set to 0 or 2" in (remarks or "").lower():
            needs_customer_and_amount_if_mode_0_or_2 = True

        init_props[name] = prop

    # Allow alias if only one exists
    if "timeStamp" not in init_props and "timestamp" in init_props:
        init_props["timeStamp"] = {
            **_iso_timestamp_schema(),
            "description": "Alias of `timestamp` (seen in code sample). Prefer `timestamp` where possible.",
        }
        timestamp_alias_present = True

    required = [r for r in required if r not in {"timestamp", "timeStamp"}]

    init_schema: Dict[str, Any] = {
        "type": "object",
        "description": "Options passed to `$.zpPayment(options)` (jQuery).",
        "additionalProperties": False,
        "properties": init_props,
    }
    if required:
        init_schema["required"] = required

    all_of: List[Dict[str, Any]] = []
    if timestamp_alias_present:
        all_of.append({"oneOf": [{"required": ["timestamp"]}, {"required": ["timeStamp"]}]})
    if needs_customer_and_amount_if_mode_0_or_2:
        all_of.append({
            "if": {"properties": {"mode": {"enum": [0, 2]}}, "required": ["mode"]},
            "then": {"required": ["customerName", "customerReference", "paymentAmount"]},
        })
    if all_of:
        init_schema["allOf"] = all_of

    # ---- Return parameters -> result schemas
    ret = sections.get("return_parameters") if isinstance(sections.get("return_parameters"), dict) else {}
    return_tables = (ret.get("tables") or []) if isinstance(ret, dict) else []
    mode0_rows: List[Dict[str, Any]] = []
    mode1_rows: List[Dict[str, Any]] = []

    for t in return_tables:
        if not isinstance(t, dict):
            continue
        label = (t.get("label") or "").lower()
        rows = t.get("rows") or []
        if "mode 1" in label:
            mode1_rows.extend(rows)
        else:
            mode0_rows.extend(rows)

    def build_result_schema(rows: List[Dict[str, Any]], description: str) -> Dict[str, Any]:
        props: Dict[str, Any] = {}
        for r in rows:
            if not isinstance(r, dict):
                continue
            param = (r.get("Parameter") or "").strip()
            if not param:
                continue
            val = r.get("Value") or ""
            sch: Dict[str, Any] = {"type": "string"}
            if val:
                sch["description"] = val

            enum_int = _extract_enum_from_value_map(val)
            if enum_int:
                sch["type"] = "integer"
                sch["enum"] = enum_int

            enum_str = _guess_string_enum(val)
            if enum_str and not enum_int:
                sch["type"] = "string"
                sch["enum"] = enum_str

            if param.lower().endswith("date"):
                if param.lower() == "processingdate":
                    sch = _iso_timestamp_schema()
                    if val:
                        sch["description"] = val
                elif param.lower() == "settlementdate":
                    sch = _iso_date_schema()
                    if val:
                        sch["description"] = val

            props[param] = sch

        return {
            "type": "object",
            "description": description,
            "additionalProperties": True,
            "properties": props,
        }

    res0_schema = build_result_schema(mode0_rows, "Result payload returned for mode 0 and 2 (redirect/callback).")
    res1_schema = build_result_schema(mode1_rows, "Result payload returned for mode 1 (tokenisation).")

    # ---- Error codes
    err = sections.get("error_codes") if isinstance(sections.get("error_codes"), dict) else {}
    err_rows = (err.get("rows") or []) if isinstance(err, dict) else []

    one_of: List[Dict[str, Any]] = []
    for r in err_rows:
        if not isinstance(r, dict):
            continue
        code = (r.get("Error Code") or "").strip()
        desc = (r.get("Description") or "").strip()
        if not code:
            continue
        if "*" in code:
            prefix = re.escape(code.replace("*", ""))
            one_of.append({"type": "string", "pattern": f"^{prefix}.*$", "description": desc})
        else:
            one_of.append({"const": code, "description": desc})

    openapi: Dict[str, Any] = {
        "openapi": "3.1.0",
        "info": {
            "title": "TravelPay / Zenith Payments - zpPayment JavaScript Plugin Schemas (v5)",
            "version": extracted_at.split("T", 1)[0],
            "summary": "OpenAPI used as a schema container for the zpPayment JavaScript plugin (not an HTTP API).",
            "description": (
                "This OpenAPI 3.1 document is intentionally not a server-side REST API specification.\n\n"
                "It exists so OpenAPI-capable tooling can consume a single canonical spec describing:\n"
                "- JavaScript plugin init options passed to `$.zpPayment(options)`\n"
                "- Result payloads delivered via redirect URL query string and/or callbackUrl\n\n"
                f"Source page: {meta.get('url')}\n"
                f"HTML SHA256: {meta.get('html_sha256')}"
            ),
        },
        "servers": [],
        "paths": {},
        "x-javascript-plugin": {
            "library": "jQuery",
            "function": "$.zpPayment",
            "initCall": "payment.init()",
            "assets": {"stylesheet": stylesheet, "javascript": javascript},
            "codeSample": code_sample_text,
        },
        "components": {
            "schemas": {
                "ZpPaymentInitOptions": init_schema,
                "ZpPaymentResultMode0or2": res0_schema,
                "ZpPaymentResultMode1": res1_schema,
                "ZpPaymentResult": {
                    "oneOf": [
                        {"$ref": "#/components/schemas/ZpPaymentResultMode0or2"},
                        {"$ref": "#/components/schemas/ZpPaymentResultMode1"},
                    ]
                },
                "ZpPaymentErrorCode": {
                    "type": "string",
                    "description": "Error codes returned by the plugin.",
                    "oneOf": one_of,
                },
            }
        },
    }

    return openapi


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True, help="Path to processed TravelPay JSON (docs/travelpay_demo.json)")
    ap.add_argument("--out", dest="out_path", required=True, help="Path to write OpenAPI output (.yaml/.yml or .json)")
    args = ap.parse_args()

    with open(args.in_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    spec = build_openapi(doc)

    if args.out_path.lower().endswith(".json"):
        with open(args.out_path, "w", encoding="utf-8") as f:
            json.dump(spec, f, indent=2, ensure_ascii=False)
            f.write("\n")
    else:
        with open(args.out_path, "w", encoding="utf-8") as f:
            f.write(yaml_dump(spec))

    print(f"Wrote OpenAPI: {args.out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
