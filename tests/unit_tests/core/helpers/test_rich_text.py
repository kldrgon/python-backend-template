import pytest

from core.helpers.rich_text import make_rich_text_snippet, rich_text_to_plain_text


@pytest.mark.asyncio
async def test_rich_text_to_plain_text_for_json_rich_text_blocks():
    value = [
        {
            "type": "heading",
            "level": 2,
            "content": [
                {"type": "text", "text": "极限的定义", "annotations": {}},
            ],
        },
        {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "设 ", "annotations": {}},
                {"type": "equation", "latex": "f(x)"},
                {"type": "text", "text": " 在 ", "annotations": {}},
                {"type": "link", "link_type": "concept", "id": "c1", "label": "极限", "nav_mode": "detail"},
                {"type": "text", "text": " 附近有定义", "annotations": {}},
            ],
        },
        {
            "type": "callout",
            "icon": None,
            "content": [
                {"type": "text", "text": "可微必连续。", "annotations": {}},
            ],
        },
        {
            "type": "equation_block",
            "latex": "f'(x) = \\lim_{\\Delta x \\to 0} \\frac{f(x + \\Delta x) - f(x)}{\\Delta x}",
        },
        {
            "type": "ref_card",
            "link_type": "problem",
            "id": "p1",
            "label": "例题1",
        },
    ]

    assert rich_text_to_plain_text(value) == (
        "极限的定义\n\n"
        "设 f(x) 在 极限 附近有定义\n\n"
        "可微必连续。\n\n"
        "f'(x) = \\lim_{\\Delta x \\to 0} \\frac{f(x + \\Delta x) - f(x)}{\\Delta x}\n\n"
        "例题1"
    )


@pytest.mark.asyncio
async def test_rich_text_to_plain_text_for_tiptap_doc():
    value = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "导数表示"},
                    {"type": "text", "text": "瞬时变化率"},
                ],
            }
        ],
    }

    assert rich_text_to_plain_text(value) == "导数表示 瞬时变化率"


@pytest.mark.asyncio
async def test_rich_text_to_plain_text_supports_simple_legacy_blocks():
    value = [
        {"text": "函数变化趋势说明"},
        {"text": "可用于定义导数"},
    ]

    assert rich_text_to_plain_text(value) == "函数变化趋势说明\n\n可用于定义导数"


@pytest.mark.asyncio
async def test_make_rich_text_snippet_uses_fallback_and_truncates():
    assert make_rich_text_snippet(None, fallback="标题", max_length=10) == "标题"
    assert make_rich_text_snippet("a" * 12, max_length=10) == "aaaaaaa..."
