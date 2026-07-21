#!/usr/bin/env python3
"""Normalize active lubricant/fluid QPLs from the US DLA QPD.

The QPD is an ASP.NET WebForms application, so this collector deliberately
uses the public search workflow rather than guessing internal identifiers.
Only factual qualification fields are retained. Addresses, telephone numbers,
test references, notes and page presentation are not republished.
"""

from __future__ import annotations

import hashlib
import html
import http.cookiejar
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "dla-qpd-lubricant-products.jsonl"
REPORT = ROOT / "data" / "dla-qpd-lubricant-products-report.json"
SEARCH_URL = "https://qpldocs.dla.mil/search/default.aspx"
HELP_URL = "https://qpldocs.dla.mil/help/default.aspx"
USER_AGENT = "MFClassifierResearch/1.0 (public-government-qualification-data research)"

# Active QPLs returned by the official FSC 9150 and FSC 6850 searches on
# 2026-07-21. FSC 6850 is deliberately narrowed to products whose governing
# specification itself establishes lubrication, lubricity improvement or an
# oil/compound function; pure cleaners, solvents, desiccants and process
# chemicals remain out of scope.
# An explicit scope makes additions/removals reviewable instead of silently
# changing the product universe when the live registry changes.
QPL_SCOPE = {
    "VV-L-825": "C", "J1899": "M", "J1966": "M", "2104": "M", "3150": "S",
    "AMS-G-4343": "G", "5606": "H", "AMS-G-6032": "G", "6081": "M", "6083": "H",
    "6085": "I", "6086": "T", "7808": "M", "7870": "S", "9000": "M",
    "10924": "G", "14107": "S", "15719": "G", "17331": "U", "17672": "H",
    "18458": "G", "21164": "G", "21260": "M", "22072": "H", "23398": "S",
    "23549": "G", "23699": "M", "23827": "G", "24131": "S", "24139": "G",
    "24508": "G", "25013": "G", "25537": "G", "27617": "G", "32014": "G",
    "32033": "S", "32073": "H", "32538": "T", "32626": "M", "46000": "S",
    "46010": "S", "46147": "S", "46150": "S", "46167": "M", "46170": "H",
    "46176": "TF", "53131": "I", "63460": "S", "81322": "G", "81827": "G",
    "83282": "H", "85694": "S", "85733": "G", "85734": "T", "87252": "TF",
    "87257": "H",
    # FSC 6850 professional lubricant / lubricity subset.
    "6529": "S", "8188": "S", "AS8660": "S", "25017": "S",
    "29608": "S", "32490": "S",
}

FSC_6850_QPLS = {"6529", "8188", "AS8660", "25017", "29608", "32490"}
FSC_6850_EXCLUDED_QPLS = {
    "372": "cleaning solvent for weapon bores",
    "P-C-444": "grease-emulsifying cleaning compound, not a lubricant",
    "680": "degreasing solvent",
    "AMS2644": "inspection penetrant",
    "3464": "desiccant",
    "17563": "component impregnant",
    "AMS-C-19853": "carbon remover",
    "AMS-C-22542": "high-pressure cleaning compound",
    "24577": "distiller scale-preventive treatment",
    "29602": "parts-washer cleaning compound",
    "32295": "non-aqueous cleaner",
    "32587": "paint remover",
    "32597": "polymer/composite cleaner",
    "32684": "vapor-degreasing solvent",
    "53021": "diesel-fuel stabilizer without an explicit lubrication function",
    "85570": "aircraft exterior cleaner",
    "85704": "turbine-engine gas-path cleaner",
    "87937": "aerospace-equipment cleaner",
}
DESIGNATION_QUALIFIER_RE = re.compile(
    r"\s+\((?=(?:SEE NOTES|MINIMUM EFFECTIVE|A REBRAND|REBRAND|A REBLEND|REBLEND|"
    r"APPROVED FOR|LIMITED USAGE|LIMITED USE|CONDITIONAL QUALIFICATION|SHALL NOT EXCEED))",
    re.IGNORECASE,
)


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def plain(fragment: str, separator: str = " ") -> str:
    fragment = re.sub(r"<br\s*/?>", separator, fragment, flags=re.I)
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    return clean(fragment)


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", clean(value)).casefold()
    return re.sub(r"[^0-9a-z]+", " ", value).strip()


def split_designation(value: str) -> tuple[str, str]:
    """Separate a commercial designation from DLA qualification qualifiers."""
    match = DESIGNATION_QUALIFIER_RE.search(value)
    if not match:
        return value, ""
    return clean(value[:match.start()]), clean(value[match.start():])


def hidden_fields(page: bytes) -> dict[str, str]:
    text = page.decode("utf-8", errors="replace")
    return {
        html.unescape(name): html.unescape(value)
        for name, value in re.findall(
            r'<input[^>]+type="hidden"[^>]+name="([^"]+)"[^>]+value="([^"]*)"', text, re.I
        )
    }


class Client:
    def __init__(self) -> None:
        jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def request(self, url: str, fields: dict[str, str] | None = None) -> tuple[str, bytes]:
        data = urllib.parse.urlencode(fields).encode() if fields is not None else None
        request = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT})
        for attempt in range(4):
            try:
                with self.opener.open(request, timeout=120) as response:
                    body = response.read()
                    final_url = response.geturl()
                time.sleep(0.08)
                return final_url, body
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)
        raise AssertionError("unreachable")


def postback(page: bytes, target: str, extra: dict[str, str] | None = None) -> dict[str, str]:
    fields = hidden_fields(page)
    fields.update({"__EVENTTARGET": target, "__EVENTARGUMENT": ""})
    if extra:
        fields.update(extra)
    return fields


def find_id(text: str, element_id: str) -> str:
    match = re.search(rf'id="{re.escape(element_id)}"[^>]*>(.*?)</(?:span|a)>', text, re.I | re.S)
    return plain(match.group(1)) if match else ""


def search_qpl(client: Client, qpl: str) -> tuple[str, bytes]:
    _, start = client.request(SEARCH_URL)
    fields = hidden_fields(start)
    fields.update({
        "Search_panel1$tbox": f"QPL-{qpl}",
        "Search_panel1$dd": "256",
        "Search_panel1$btn": "Search",
    })
    _, results = client.request(SEARCH_URL, fields)
    text = results.decode("utf-8", errors="replace")
    rows = re.findall(r'<tr[^>]*class="(?:grid_item|alternate_item)"[^>]*>(.*?)</tr>', text, re.I | re.S)
    exact_target = ""
    for row in rows:
        if re.search(rf"\bQPL-{re.escape(qpl)}\b", plain(row), re.I):
            event = re.search(r"__doPostBack\(&#39;([^&]+)&#39;", row)
            if event:
                exact_target = html.unescape(event.group(1))
                break
    if not exact_target:
        raise AssertionError(f"exact QPL not found: {qpl}")
    return client.request(SEARCH_URL, postback(results, exact_target))


def part_rows(page: bytes) -> list[tuple[str, str]]:
    text = page.decode("utf-8", errors="replace")
    table = re.search(r'<table[^>]+id="Lu_gov_DG".*?</table>', text, re.I | re.S)
    assert table, "government designation table missing"
    rows = []
    for row in re.findall(r'<tr[^>]*class="(?:grid_item|alternate_item)"[^>]*>(.*?)</tr>', table.group(0), re.I | re.S):
        event = re.search(r'WebForm_PostBackOptions\(&quot;([^&]+btnGovPartNo)&quot;', row)
        designation = re.search(r'btnGovPartNo"[^>]*>(.*?)</a>', row, re.I | re.S)
        if event and designation:
            rows.append((html.unescape(event.group(1)), plain(designation.group(1))))
    return rows


def page_count(page: bytes) -> int:
    text = page.decode("utf-8", errors="replace")
    match = re.search(r'id="Lu_gov_Datagrid_navigation1_lblPageCount"[^>]*>\s*Page&nbsp;\d+&nbsp;of&nbsp;(\d+)', text, re.I)
    return int(match.group(1)) if match else 1


def parse_print_page(body: bytes, url: str, govt_designation: str) -> tuple[dict, list[dict], int]:
    text = body.decode("utf-8", errors="replace")
    header = {
        "qualifying_activity": find_id(text, "lblQual"),
        "fsc": find_id(text, "lblFsc"),
        "document_date": find_id(text, "lblDocDate"),
        "document_id": find_id(text, "lblDocId"),
        "qpl_number": find_id(text, "lblQpl"),
        "qpl_status": find_id(text, "lblStatus"),
        "title": find_id(text, "lblTitle"),
    }
    update = re.search(r"last updated on\s+([0-9/]+)", plain(text), re.I)
    header["qpd_update_date"] = update.group(1) if update else ""
    table = re.search(r'<table[^>]+id="tblSource".*?</table>', text, re.I | re.S)
    assert table, f"manufacturer table missing: {url}"
    products = []
    empty_designations = 0
    for row in re.findall(r'<tr[^>]*class="print_td"[^>]*>(.*?)</tr>', table.group(0), re.I | re.S):
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.I | re.S)
        if len(cells) != 2:
            continue
        designation = re.sub(r'<br\s*/?>\s*NOTES:.*', '', cells[0], flags=re.I | re.S)
        designation = plain(designation)
        if not designation:
            empty_designations += 1
            continue
        product_name, designation_qualifier = split_designation(designation)
        info = cells[1]
        def field(label: str) -> str:
            match = re.search(rf'{re.escape(label)}:\s*</span>(?:<br\s*/?>)+<span>(.*?)</span>', info, re.I | re.S)
            if not match:
                match = re.search(rf'{re.escape(label)}:\s*([^<]+)', plain(info), re.I)
            return plain(match.group(1), " / ") if match else ""
        def inline(label: str) -> str:
            match = re.search(rf'{re.escape(label)}:\s*([^<]*)</span>', info, re.I)
            return clean(match.group(1)) if match else ""
        products.append({
            **header,
            "government_designation": govt_designation,
            "manufacturer_designation": designation,
            "product_name_standardized": product_name,
            "designation_qualifier": designation_qualifier,
            "cage_code": inline("Cage Code"),
            "company": field("Company Name"),
            "certified_status": inline("Certified Status").upper(),
            "sam_status": inline("SAM Status"),
            "stop_ship": inline("Stop Ship").upper(),
            "source_type": inline("Source Type"),
            "source_url": url,
        })
    fact_rows = [{key: value for key, value in row.items() if key not in {"source_url", "source_page_facts_sha256"}} for row in products]
    page_facts = {"government_designation": govt_designation, "header": header, "products": fact_rows}
    page_facts_sha256 = hashlib.sha256(json.dumps(page_facts, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    for product in products:
        product["source_page_facts_sha256"] = page_facts_sha256
    return header, products, empty_designations


def technical(name: str, government: str, title: str) -> dict[str, list[str]]:
    value = " ".join([name, government, title]).upper()
    return {
        "sae": sorted(set(re.findall(r"\b(?:0W|5W|10W|15W|20W|25W)(?:[- ]?\d{2,3})?\b|\bSAE\s+\d{2,3}\b", value))),
        "iso_vg": sorted(set(re.findall(r"\bISO\s*(?:VG\s*)?(\d{1,4})\b", value)), key=int),
        "nlgi": sorted(set(re.findall(r"\bNLGI\s*(?:GRADE\s*)?([0-6](?:\.5)?)\b", value))),
        "nato_codes": sorted(set(re.findall(r"\b(?:G|H|O|S)-\d{3,4}\b", value))),
    }


def lifecycle(row: dict) -> str:
    if row["stop_ship"] == "YES":
        return "stop_ship"
    if row["sam_status"].casefold() not in {"", "active"}:
        return "sam_inactive_source_review"
    return {
        "GREEN": "qualified_source_certified",
        "YELLOW": "qualified_source_due_for_certification",
        "RED": "qualification_overdue_contact_qa",
    }.get(row["certified_status"], "published_qualification_status_unresolved")


def main() -> None:
    assert len(QPL_SCOPE) == 62
    client = Client()
    occurrences = []
    qpl_headers = {}
    plant_rows_excluded = 0
    government_parts = 0
    for index, (qpl, family) in enumerate(QPL_SCOPE.items(), 1):
        parts_url, first_page = search_qpl(client, qpl)
        pages = [first_page]
        for number in range(2, page_count(first_page) + 1):
            fields = hidden_fields(first_page)
            fields.update({
                "Lu_gov$Datagrid_navigation1$txtPgNum": str(number),
                "Lu_gov$Datagrid_navigation1$btnGoTo": "Go to Page",
            })
            _, page = client.request(parts_url, fields)
            pages.append(page)
        for page in pages:
            for target, govt_designation in part_rows(page):
                government_parts += 1
                _, selected = client.request(parts_url, postback(page, target))
                selected_text = selected.decode("utf-8", errors="replace")
                match = re.search(r"popup\(&#39;(\d+)&#39;\)", selected_text)
                if not match:
                    raise AssertionError(f"manufacturer print ID missing: {qpl} {govt_designation}")
                print_url = f"https://qpldocs.dla.mil/search/print_govt_mfg.aspx?govt={match.group(1)}"
                final_url, printable = client.request(print_url)
                header, products, excluded = parse_print_page(printable, final_url, govt_designation)
                assert header["qpl_number"].upper() == f"QPL-{qpl}".upper(), (qpl, header)
                plant_rows_excluded += excluded
                qpl_headers[qpl] = header
                for product in products:
                    product["family_code"] = family
                    product["source_id"] = "DLA_QPD_FSC_6850_LUBRICANT_SCOPE" if qpl in FSC_6850_QPLS else "DLA_QPD_FSC_9150"
                    occurrences.append(product)
        print(f"[{index:02d}/{len(QPL_SCOPE)}] QPL-{qpl}: {sum(r['qpl_number'].upper() == ('QPL-' + qpl).upper() for r in occurrences)} product occurrences", flush=True)

    grouped: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    for row in occurrences:
        grouped[(row["source_id"], normalize(row["company"]), normalize(row["manufacturer_designation"]), row["family_code"])].append(row)
    records = []
    for key, rows in sorted(grouped.items()):
        first = rows[0]
        approvals = sorted({
            (r["qpl_number"], r["document_id"], r["government_designation"], r["source_url"], r["source_page_facts_sha256"])
            for r in rows
        })
        statuses = sorted({lifecycle(r) for r in rows})
        lifecycle_status = statuses[0] if len(statuses) == 1 else "mixed_qualification_lifecycle_review"
        fingerprint = hashlib.sha256("|".join(key[1:]).encode()).hexdigest()[:16]
        records.append({
            "source_id": first["source_id"],
            "source_record_id": f"DLA-QPD-{fingerprint}",
            "source_url": SEARCH_URL,
            "help_url": HELP_URL,
            "snapshot_date": date.today().isoformat(),
            "market": "United States / qualified sources may be international",
            "company": first["company"],
            "cage_codes": sorted({r["cage_code"] for r in rows if r["cage_code"]}),
            "product_name": first["product_name_standardized"],
            "manufacturer_designations_raw": sorted({r["manufacturer_designation"] for r in rows}),
            "designation_qualifiers": sorted({r["designation_qualifier"] for r in rows if r["designation_qualifier"]}),
            "family_code": first["family_code"],
            "lifecycle_status": lifecycle_status,
            "qualification_statuses": statuses,
            "certified_statuses": sorted({r["certified_status"] for r in rows}),
            "sam_statuses": sorted({r["sam_status"] for r in rows}),
            "stop_ship_values": sorted({r["stop_ship"] for r in rows}),
            "source_types": sorted({r["source_type"] for r in rows}),
            "technical": technical(first["product_name_standardized"], " ".join(r["government_designation"] for r in rows), " ".join(r["title"] for r in rows)),
            "qualifications": [
                {"qpl_number": q, "document_id": d, "government_designation": g, "source_url": u, "source_page_facts_sha256": h}
                for q, d, g, u, h in approvals
            ],
            "source_occurrence_count": len(rows),
        })

    output_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records)
    OUTPUT.write_text(output_text, encoding="utf-8")
    source_fact_pages = sorted({(row["source_url"], row["source_page_facts_sha256"]) for row in occurrences})
    manifest = "\n".join(f"{url}\t{digest}" for url, digest in source_fact_pages) + "\n"
    report = {
        "schema_version": 1,
        "status": "official_government_qualified_product_registry_normalized",
        "snapshot_date": date.today().isoformat(),
        "source_url": SEARCH_URL,
        "help_url": HELP_URL,
        "fsc_scope": ["9150", "6850 (lubricant/lubricity subset only)"],
        "fsc_6850_excluded_active_qpls": {f"QPL-{qpl}": reason for qpl, reason in FSC_6850_EXCLUDED_QPLS.items()},
        "active_qpls_in_scope": len(QPL_SCOPE),
        "qpls_by_fsc": {"9150": 56, "6850_lubricant_scope": len(FSC_6850_QPLS)},
        "qpl_numbers": [f"QPL-{qpl}" for qpl in QPL_SCOPE],
        "government_designations": government_parts,
        "published_manufacturer_product_occurrences": len(occurrences),
        "normalized_products": len(records),
        "normalized_products_by_source": dict(sorted(Counter(row["source_id"] for row in records).items())),
        "duplicate_qualification_occurrences_merged": len(occurrences) - len(records),
        "plant_rows_without_product_designation_excluded": plant_rows_excluded,
        "families": dict(sorted(Counter(row["family_code"] for row in records).items())),
        "lifecycle_statuses": dict(sorted(Counter(row["lifecycle_status"] for row in records).items())),
        "certified_statuses_by_occurrence": dict(sorted(Counter(row["certified_status"] for row in occurrences).items())),
        "stop_ship_by_occurrence": dict(sorted(Counter(row["stop_ship"] for row in occurrences).items())),
        "source_fact_pages": len(source_fact_pages),
        "source_facts_manifest_sha256": hashlib.sha256(manifest.encode()).hexdigest(),
        "normalized_output_sha256": hashlib.sha256(output_text.encode()).hexdigest(),
        "qpl_metadata": qpl_headers,
        "rights_note": "DLA QPD publishes official qualification data for sourcing decisions; QPL public-release documents state distribution is unlimited. Only factual product and qualification fields are retained with attribution.",
        "scope_note": "All active FSC 9150 QPLs are included. From FSC 6850 only QPL-6529, 8188, AS8660, 25017, 29608 and 32490 are included because their governing titles explicitly establish an oil, silicone compound, cleaning-lubricating compound, corrosion/lubricity inhibitor or lubricity-improver function; pure cleaners, solvents and unrelated chemicals are excluded.",
        "privacy_and_scope_note": "Addresses, telephone numbers, websites, test references, notes and page presentation are deliberately omitted. Plant rows without a manufacturer designation are not products and are excluded.",
        "status_note": "GREEN, YELLOW, RED, SAM status and Stop Ship remain distinct lifecycle evidence. Publication in QPD is not flattened into a generic active-product claim.",
        "grain_note": "One normalized row is company + manufacturer designation + professional family. Multiple government designations and QPL occurrences are retained as qualifications on that row.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ["normalized_products", "published_manufacturer_product_occurrences", "government_designations", "families", "lifecycle_statuses"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
