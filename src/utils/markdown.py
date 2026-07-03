def parse_message_blocks(content: str) -> list[str]:
    """Split markdown content by '---' separators, strip whitespace, and filter empty blocks."""
    return [b.strip() for b in content.split("---") if b.strip()]


def filter_month_files(md_files: list[str], start_month: str | None, end_month: str | None) -> list[str]:
    """Filter a sorted list of YYYY_MM.md filenames by an inclusive month range."""
    result = []
    for f in md_files:
        month_key = f[:-3]
        if start_month and month_key < start_month:
            continue
        if end_month and month_key > end_month:
            continue
        result.append(f)
    return result
