"""Turn the supplied BNS and IPC PDFs into section-level JSONL files.

Run: uv run python -m building_with_rag.ingest
"""

import hashlib
import json
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

import pypdf
from pypdf import PdfReader

RAW_DIR = Path("data/raw")
OUT_DIR = Path("data/processed")

ACTS = {
    "bns": {
        "pdf": "BNS_2023_bare_act.pdf",
        "out": "bns_sections.jsonl",
        "act": "BNS_2023",
        "act_label": "Bharatiya Nyaya Sanhita, 2023",
        "status": "in_force",
    },
    "ipc": {
        "pdf": "IPC_1860_bare_act.pdf",
        "out": "ipc_sections.jsonl",
        "act": "IPC_1860",
        "act_label": "Indian Penal Code, 1860",
        "status": "repealed",
    },
}

CHAPTER_RE = re.compile(r"^CHAPTER\s+([IVXL]+[A-Z]?)\s*$")
FOOTNOTE_LEAD_RE = re.compile(
    r"^\d{1,3}\.\s+(Subs\.|Ins\.|Rep\.|Omitted|Added|Renumbered|Re-numbered|The words|The word |"
    r"The figures|The brackets|The Act|The original|See |Clause|Cl\.|Sub-section|Paragraph|Proviso|"
    r"Original|Now |Ss?\. )"
)
# Leftover footnote wording inside a section's text means the page-footer cut missed something.
FOOTNOTE_TRACE_RE = re.compile(r"\b(Subs\.|Ins\.) by (Act|the A\. ?O\.|s\.)")


@dataclass
class Line:
    page: int  # 1-based
    text: str


@dataclass
class Section:
    number: str  # "103" or "376A"
    chapter: str
    chapter_title: str
    heading_lines: list[str]
    body: list[Line] = field(default_factory=list)
    page_start: int = 0
    reasons: list[str] = field(default_factory=list)


def _heading_key(text: str) -> str:
    return squash(text.replace("’", "'").replace("‘", "'"))


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def squash(text: str) -> str:
    """Whitespace-free lowercase key, robust to the PDF's stray intra-word spaces."""
    return re.sub(r"\s+", "", text).lower()


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def provenance_hashes() -> dict[str, str]:
    text = (RAW_DIR / "PROVENANCE.md").read_text(encoding="utf-8")
    return dict(re.findall(r"\|\s*`([^`]+\.pdf)`.*?`([0-9a-f]{64})`\s*\|", text))


def read_pages(path: Path) -> list[list[str]]:
    reader = PdfReader(path)
    return [(page.extract_text() or "").splitlines() for page in reader.pages]


def clean_pages(key: str, pages: list[list[str]]) -> list[Line]:
    """Drop repeated page headers, IPC footnote blocks and page numbers; return flat lines."""
    counts: Counter[str] = Counter()
    for page in pages:
        counts.update({squash(line) for line in page if line.strip()})
    repeated = {k for k, n in counts.items() if n >= 0.5 * len(pages) and len(k) < 60}

    out: list[Line] = []
    for number, page in enumerate(pages, start=1):
        lines = [line.rstrip() for line in page]
        if key == "ipc":
            lines = _drop_footnotes(lines)
        for line in lines:
            stripped = line.strip()
            if not stripped or squash(stripped) in repeated:
                continue
            if re.fullmatch(r"\d{1,3}", stripped) and key == "ipc":
                continue  # page number
            if re.search(r"HomePage\s*$", stripped) or stripped.startswith("Note: For Reference"):
                continue
            out.append(Line(number, stripped))
    return out


def _drop_footnotes(lines: list[str]) -> list[str]:
    """Remove IPC footnotes and separator rules.

    Footnotes that run over from the previous page sit before the body; the page's own footnotes
    sit after it. Once body text has started, the first footnote line ends the page.
    """
    out: list[str] = []
    seen_body = False
    i = 0
    while i < len(lines):
        text = lines[i].strip()
        if re.match(r"^-{20,}$", text):
            i += 1
        elif FOOTNOTE_LEAD_RE.match(text):
            if seen_body:
                # Trailing footnotes: skip to the next section marker or chapter heading, if any.
                i += 1
                while i < len(lines) and not _starts_section(lines[i].strip()):
                    i += 1
                continue
            i += 1
            taken = 0
            while i < len(lines) and taken < 4 and _is_footnote_continuation(lines[i].strip()):
                i += 1
                taken += 1
        else:
            if text and not re.fullmatch(r"\d{1,3}", text):
                seen_body = True
            out.append(lines[i])
            i += 1
    return out


def _starts_section(text: str) -> bool:
    return bool(CHAPTER_RE.match(text) or re.fullmatch(r"\d{1,3}[A-Z]{0,2}\.", text))


def _is_footnote_continuation(text: str) -> bool:
    if not text or CHAPTER_RE.match(text) or re.fullmatch(r"\d{1,3}[A-Z]{0,2}\.", text):
        return False
    return not re.match(r"^(\d+\*+\[)*\d{1,3}[A-Z]{0,2}\.\s", text) and not text[0].isupper()


def read_chapter(lines: list[Line], i: int) -> tuple[str, str, int]:
    """Parse a CHAPTER line plus its upper-case title lines. Returns (chapter, title, next_i)."""
    chapter = CHAPTER_RE.match(lines[i].text).group(1)
    j, title = i + 1, []
    while j < len(lines) and len(title) < 3 and _is_title_line(lines[j].text):
        title.append(lines[j].text)
        j += 1
    return chapter, norm(" ".join(title)), j


def _is_title_line(text: str) -> bool:
    return text.isupper() and not CHAPTER_RE.match(text) and not re.match(r"^\d", text)


def bns_index_headings(lines: list[Line]) -> dict[int, str]:
    """Headings from the arrangement-of-sections index (before the corresponding table)."""
    start = next(i for i, ln in enumerate(lines) if "ARRANGEMENT OF SECTIONS" in ln.text)
    end = next(i for i, ln in enumerate(lines) if "CORRESPONDING SECTION TABLE" in ln.text)
    headings: dict[int, str] = {}
    current: int | None = None
    for ln in lines[start:end]:
        m = re.match(r"^(\d{1,3})\.\s+(.*)$", ln.text)
        if m and int(m.group(1)) == (current or 0) + 1:
            current = int(m.group(1))
            headings[current] = m.group(2)
        elif current is not None and not CHAPTER_RE.match(ln.text) and not _is_title_line(ln.text):
            if not headings[current].rstrip().endswith("."):
                headings[current] += " " + ln.text
    return headings


def parse_bns(lines: list[Line]) -> list[Section]:
    index = bns_index_headings(lines)
    body_start = next(i for i, ln in enumerate(lines) if re.match(r"^1\.\s*\(1\)", ln.text))
    # Step back to the CHAPTER I heading just before section 1.
    chapter_i = max(i for i in range(body_start) if CHAPTER_RE.match(lines[i].text))
    # The sentinel collects lines above section 1 so its heading can be split off like the others.
    sections: list[Section] = [Section("0", "", "", [], [], 0)]
    chapter, chapter_title = "", ""
    last = 0
    i = chapter_i
    while i < len(lines):
        text = lines[i].text
        if text.startswith("—————"):
            break
        if CHAPTER_RE.match(text):
            chapter, chapter_title, i = read_chapter(lines, i)
            continue
        m = re.match(r"^(\d{1,3})\.(?=\s*\S)", text)
        if m and int(m.group(1)) == last + 1:
            last = int(m.group(1))
            sections.append(
                Section(str(last), chapter, chapter_title, [], [lines[i]], lines[i].page)
            )
        elif sections:
            sections[-1].body.append(lines[i])
        i += 1

    for prev, sec in zip(sections, sections[1:], strict=False):
        _split_bns_heading(sec, index.get(int(sec.number)), prev)
    return sections[1:]


def _split_bns_heading(sec: Section, index_heading: str | None, prev: Section) -> None:
    """Move the heading lines that precede a section start out of the previous section's body."""
    if index_heading is None:
        sec.reasons.append("no heading in index")
        return
    target = _heading_key(index_heading)
    tail = prev.body
    scored = [
        (
            SequenceMatcher(
                None, _heading_key("".join(ln.text for ln in tail[-k:])), target
            ).ratio(),
            k,
        )
        for k in range(1, min(6, len(tail)) + 1)
    ]
    best, k = max(scored, default=(0.0, 0))
    if best < 0.85:
        sec.heading_lines = [index_heading]
        sec.reasons.append("heading not found above section text; taken from index")
        return
    sec.heading_lines = [ln.text for ln in tail[-k:]]
    del tail[-k:]
    # Drop group titles such as "Of breach of contract ..." that sit above the heading.
    n = 0
    while n < min(3, len(tail)) and not re.search(r"[.;:,—]\s*$", tail[-1 - n].text):
        n += 1
    if n and tail[-n].text.startswith("Of "):
        del tail[-n:]


def parse_ipc(lines: list[Line]) -> list[Section]:
    sections: list[Section] = []
    chapter, chapter_title = "", ""
    i = 0
    while i < len(lines):
        text = lines[i].text
        if CHAPTER_RE.match(text):
            chapter, chapter_title, i = read_chapter(lines, i)
            continue
        m = re.fullmatch(r"(\d{1,3}[A-Z]{0,2})\.", text)
        if m:
            num = m.group(1)
            start_re = re.compile(rf"^(?:\d+\*+\[?)*{re.escape(num)}\.\s")
            j = i + 1
            while j < len(lines) and j - i <= 8 and not start_re.match(lines[j].text):
                j += 1
            sec = Section(num, chapter, chapter_title, [], [], lines[i].page)
            if j < len(lines) and start_re.match(lines[j].text):
                sec.heading_lines = [ln.text for ln in lines[i + 1 : j]]
                i = j
            else:
                sec.reasons.append("section start line not found after number")
                i += 1
            sections.append(sec)
            continue
        if sections:
            sections[-1].body.append(lines[i])
        i += 1
    return sections


def to_record(sec: Section, spec: dict, key: str, sha: str, version: str) -> dict:
    heading = norm(" ".join(sec.heading_lines))
    text = norm(" ".join(ln.text for ln in sec.body))
    if key == "ipc":
        text = re.sub(rf"^(?:\d+\*+\[?)*{re.escape(sec.number)}\.\s+", "", text)
        if heading and squash(text).startswith(squash(heading)):
            text = _strip_prefix(text, heading)
    else:
        text = re.sub(rf"^{re.escape(sec.number)}\.\s+", "", text)
    reasons = list(sec.reasons)
    digits = re.match(r"\d+", sec.number).group(0)
    if sec.number != digits:
        reasons.append("lettered section number; section_number is the integer part")
    if not text:
        reasons.append("empty text")
    if not heading:
        reasons.append("empty heading")
    if not sec.chapter:
        reasons.append("no chapter")
    if FOOTNOTE_TRACE_RE.search(text):
        reasons.append("possible footnote text inside section")
    last_page = sec.body[-1].page if sec.body else sec.page_start
    return {
        "section_id": f"{key}:{sec.number}",
        "act": spec["act"],
        "act_label": spec["act_label"],
        "status": spec["status"],
        "chapter": sec.chapter,
        "chapter_title": sec.chapter_title,
        "section_number": int(digits),
        "heading": heading,
        "text": text,
        "source_pdf": spec["pdf"],
        "source_sha256": sha,
        "parser": "pypdf",
        "parser_version": version,
        "source_status_version": None,
        "needs_review": bool(reasons),
        "review_reasons": reasons,
        "page_start": sec.page_start,
        "page_end": last_page,
    }


def _strip_prefix(text: str, heading: str) -> str:
    """Remove a leading 'Heading.--' from the body, matching whitespace loosely."""
    target = squash(heading)
    consumed = ""
    for idx, ch in enumerate(text):
        if not ch.isspace():
            consumed += ch.lower()
        if consumed == target:
            rest = text[idx + 1 :]
            return re.sub(r"^[.\s]*(?:[-–—]\s*)+", "", rest) or text
    return text


def dedupe(records: list[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    for rec in records:
        prior = seen.get(rec["section_id"])
        if prior is None:
            seen[rec["section_id"]] = rec
        elif prior["text"] != rec["text"]:
            prior["needs_review"] = True
            prior["review_reasons"].append("duplicate section number with different text")
    return list(seen.values())


def existing_sha(path: Path) -> str | None:
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as fh:
        first = fh.readline()
    try:
        return json.loads(first)["source_sha256"] if first else None
    except (json.JSONDecodeError, KeyError):
        return None


def write_atomic(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def ingest() -> None:
    expected = provenance_hashes()
    for key, spec in ACTS.items():
        pdf = RAW_DIR / spec["pdf"]
        if not pdf.exists():
            raise SystemExit(f"Missing input: {pdf}")
        sha = sha256_of(pdf)
        if sha != expected.get(spec["pdf"]):
            raise SystemExit(f"SHA-256 of {pdf} does not match data/raw/PROVENANCE.md; stopping.")
        out = OUT_DIR / spec["out"]
        if existing_sha(out) == sha:
            print(f"{key}: up to date ({out}), left untouched")
            continue
        lines = clean_pages(key, read_pages(pdf))
        sections = parse_bns(lines) if key == "bns" else parse_ipc(lines)
        records = dedupe([to_record(s, spec, key, sha, pypdf.__version__) for s in sections])
        write_atomic(out, records)
        flagged = sum(r["needs_review"] for r in records)
        print(f"{key}: wrote {len(records)} records to {out} ({flagged} need review)")


if __name__ == "__main__":
    ingest()
