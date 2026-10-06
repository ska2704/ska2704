"""Read the canonical native profile content without changing its claims."""

from html.parser import HTMLParser
from pathlib import Path
import re


def _normalize_space(value: str) -> str:
    return " ".join(value.split())


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.fragments: list[str] = []

    def handle_data(self, data: str) -> None:
        self.fragments.append(data)


def _html_text(value: str) -> str:
    parser = _TextParser()
    parser.feed(value)
    parser.close()
    return _normalize_space("".join(parser.fragments))


class _ProjectTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.projects: list[dict] = []
        self.current: dict | None = None
        self.capture: str | None = None
        self.fragments: list[str] = []
        self.paragraph_index = 0
        self.in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "td":
            if self.current is not None:
                raise ValueError("Nested project table cells are unsupported")
            self.current = {"label": "", "title": "", "url": "", "description": "", "tools": []}
            self.paragraph_index = 0
        elif self.current is not None:
            if tag == "sub":
                self.capture, self.fragments = "label", []
            elif tag == "h3":
                self.in_title = True
                self.capture, self.fragments = "title", []
            elif tag == "a" and self.in_title:
                self.current["url"] = dict(attrs).get("href") or ""
            elif tag == "p":
                self.paragraph_index += 1
                if self.paragraph_index == 1:
                    self.capture, self.fragments = "description", []
            elif tag == "code":
                self.capture, self.fragments = "tool", []

    def handle_data(self, data: str) -> None:
        if self.current is not None and self.capture is not None:
            self.fragments.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.current is None:
            return
        capture_end = {"sub": "label", "h3": "title", "p": "description", "code": "tool"}
        if capture_end.get(tag) == self.capture:
            value = _normalize_space("".join(self.fragments))
            if self.capture == "tool":
                self.current["tools"].append(value)
            elif self.capture == "title":
                self.current["title"] = value.removesuffix("↗").rstrip()
            else:
                self.current[self.capture] = value
            self.capture, self.fragments = None, []
        if tag == "h3":
            self.in_title = False
        elif tag == "td":
            if not all(self.current[key] for key in ("label", "title", "url", "description", "tools")):
                raise ValueError("A project card is missing content")
            self.projects.append(self.current)
            self.current = None


def _markdown_paragraphs(value: str) -> list[str]:
    """Preserve Markdown styling and links, splitting each native list item."""
    result: list[str] = []
    for block in re.split(r"\n\s*\n", value.strip()):
        lines = block.splitlines()
        if not any(line.strip() for line in lines):
            continue
        if any(re.match(r"^\s*[-*+]\s+", line) for line in lines):
            item: list[str] = []
            for line in lines:
                if re.match(r"^\s*[-*+]\s+", line) and item:
                    result.append(_normalize_space(" ".join(item)))
                    item = []
                item.append(line.strip())
            if item:
                result.append(_normalize_space(" ".join(item)))
        else:
            result.append(_normalize_space(" ".join(lines)))
    return result


def load_profile(path: str | Path) -> dict:
    """Return profile content for display, keeping Markdown in native prose.

    ``intro`` has two paragraphs. ``projects`` supplies the Selected builds
    cards, so that heading is not repeated in ``sections``. HTML text in
    cards, the final details block, and the footer is entity-decoded;
    Markdown strings retain their original bold, code, links and entities.
    """
    source = Path(path).read_text(encoding="utf-8")
    table = re.search(r"<table\b[^>]*>.*?</table>", source, flags=re.S | re.I)
    details = re.search(r"<details\b[^>]*>.*?</details>", source, flags=re.S | re.I)
    if table is None or details is None:
        raise ValueError("Canonical profile must contain project table and beyond-code details")

    parser = _ProjectTableParser()
    parser.feed(table.group())
    parser.close()

    summary = re.search(r"<summary\b[^>]*>(.*?)</summary>", details.group(), flags=re.S | re.I)
    beyond_text = re.search(r"<p\b[^>]*>(.*?)</p>", details.group(), flags=re.S | re.I)
    if summary is None or beyond_text is None:
        raise ValueError("Beyond-code details must contain a summary and paragraph")

    tail = source[details.end():]
    footer = re.search(r"<p\b[^>]*>(.*?)</p>", tail, flags=re.S | re.I)
    if footer is None:
        raise ValueError("Canonical profile must contain the closing footer")

    native_body = source[:details.start()].replace(table.group(), "")
    heading_matches = list(re.finditer(r"^##\s+(.+)$", native_body, flags=re.M))
    intro_end = heading_matches[0].start() if heading_matches else len(native_body)
    sections: list[dict] = []
    for index, match in enumerate(heading_matches):
        end = heading_matches[index + 1].start() if index + 1 < len(heading_matches) else len(native_body)
        heading = match.group(1).strip()
        paragraphs = _markdown_paragraphs(native_body[match.end():end])
        if heading == "Selected builds":
            if paragraphs:
                raise ValueError("Selected builds contains prose outside its parsed cards")
            continue
        sections.append({"heading": heading, "paragraphs": paragraphs})

    return {
        "intro": _markdown_paragraphs(native_body[:intro_end]),
        "projects": parser.projects,
        "sections": sections,
        "beyond": {"heading": _html_text(summary.group(1)), "text": _html_text(beyond_text.group(1))},
        "footer": _html_text(footer.group(1)),
    }
