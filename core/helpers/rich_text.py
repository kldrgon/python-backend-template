from typing import Any


def rich_text_to_plain_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        normalized = _normalize_whitespace(value)
        return normalized or None
    if isinstance(value, dict):
        blocks = _extract_blocks_from_tiptap_doc(value)
    elif isinstance(value, list):
        blocks = value
    else:
        normalized = _normalize_whitespace(str(value))
        return normalized or None

    texts = [_extract_block_text(block) for block in blocks if isinstance(block, dict)]
    merged = "\n\n".join(text for text in texts if text).strip()
    return merged or None


def make_rich_text_snippet(value: Any, *, fallback: str | None = None, max_length: int = 200) -> str:
    plain_text = rich_text_to_plain_text(value)
    base = plain_text or fallback or ""
    normalized = _normalize_whitespace(base)
    if len(normalized) <= max_length:
        return normalized
    if max_length <= 3:
        return normalized[:max_length].rstrip()
    return normalized[: max_length - 3].rstrip() + "..."


def _extract_blocks_from_tiptap_doc(value: dict[str, Any]) -> list[dict[str, Any]]:
    if value.get("type") != "doc":
        return []
    content = value.get("content")
    if not isinstance(content, list):
        return []
    return [item for item in content if isinstance(item, dict)]


def _extract_block_text(block: dict[str, Any]) -> str:
    block_type = block.get("type")
    if block_type is None:
        if "text" in block:
            return _normalize_whitespace(str(block.get("text") or ""))
        if "latex" in block:
            return _normalize_whitespace(str(block.get("latex") or ""))
        return _extract_inline_text(block.get("content"))
    if block_type in {
        "paragraph",
        "heading",
        "bulleted_list_item",
        "numbered_list_item",
        "blockquote",
        "callout",
    }:
        return _extract_inline_text(block.get("content"))
    if block_type == "code_block":
        return _normalize_whitespace(str(block.get("code") or ""))
    if block_type == "equation_block":
        return _normalize_whitespace(str(block.get("latex") or ""))
    if block_type == "ref_card":
        return _normalize_whitespace(str(block.get("label") or block.get("id") or ""))
    if block_type == "image":
        return _normalize_whitespace(str(block.get("alt") or ""))
    if block_type == "divider":
        return ""
    return _extract_inline_text(block.get("content"))


def _extract_inline_text(value: Any) -> str:
    if not isinstance(value, list):
        return ""

    parts: list[str] = []
    for node in value:
        if not isinstance(node, dict):
            continue
        node_type = node.get("type")
        if node_type == "text" or (node_type is None and "text" in node):
            parts.append(str(node.get("text") or ""))
        elif node_type == "equation" or (node_type is None and "latex" in node):
            parts.append(str(node.get("latex") or ""))
        elif node_type == "link":
            parts.append(str(node.get("label") or node.get("id") or ""))
        else:
            parts.append(_extract_inline_text(node.get("content")))
    return _normalize_whitespace(" ".join(part for part in parts if part))


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split()).strip()
