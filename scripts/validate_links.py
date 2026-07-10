#!/usr/bin/env python3
"""validate_links.py

Scans all markdown (.md) files in the repository for links, parses both relative
links and 'file:///' absolute links, and verifies that the target files/directories
exist.
"""

import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse, unquote

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Regex to find markdown links: [label](url)
LINK_RE = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')


def validate_markdown_file(file_path: Path) -> list[str]:
    errors = []
    content = file_path.read_text(encoding='utf-8')
    lines = content.splitlines()

    for idx, line in enumerate(lines, 1):
        for match in LINK_RE.finditer(line):
            label, url = match.groups()
            
            # Clean up anchors/hashes (e.g. #L12-L24)
            url_clean = url.split('#')[0]
            if not url_clean:
                continue  # Local anchor reference in the same file

            # Ignore web links (http, https, etc.)
            if url_clean.startswith(('http://', 'https://', 'mailto:')):
                continue

            target_path = None

            # Handle file:/// absolute URLs
            if url_clean.startswith('file:///'):
                # Extract the path from the URL
                parsed = urlparse(url_clean)
                # Unquote URL-encoded characters (like %20 for space)
                raw_path = unquote(parsed.path)
                
                # Under Windows, the urlparse path might start with a leading slash before drive letter, e.g. /f:/Github
                if raw_path.startswith('/') and len(raw_path) > 2 and raw_path[2] == ':':
                    raw_path = raw_path[1:]
                
                # Check path absolute or relative to project root
                test_path = Path(raw_path)
                if test_path.exists():
                    target_path = test_path
                else:
                    # Fallback: check relative to project root if it was written relative
                    target_path = PROJECT_ROOT / raw_path

            else:
                # Handle relative path links
                target_path = (file_path.parent / url_clean).resolve()

            # Verify existence
            if target_path is None or not target_path.exists():
                errors.append(
                    f"Line {idx}: Broken link '{url}' (label: '{label}'). Resolved to: '{target_path}'"
                )

    return errors


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass  # In case stdout doesn't support reconfigure

    print("Starting markdown link validation...")
    md_files = []
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Skip virtual env and dot directories
        if any(p in root for p in ['.venv', '.git', '.github', '.jules', '.mypy_cache', 'node_modules', 'htmlcov']):
            continue
        for file in files:
            if file.endswith('.md'):
                md_files.append(Path(root) / file)

    total_errors = 0
    total_files = len(md_files)

    for md_file in md_files:
        rel_path = md_file.relative_to(PROJECT_ROOT)
        try:
            errors = validate_markdown_file(md_file)
            if errors:
                print(f"\n❌ {rel_path} ({len(errors)} errors):")
                for err in errors:
                    print(f"   {err}")
                total_errors += len(errors)
            else:
                print(f"✅ {rel_path} (OK)")
        except Exception as e:
            print(f"❌ {rel_path}: Failed to process: {e}")
            total_errors += 1

    print("\n" + "=" * 40)
    print(f"Scanned {total_files} markdown files.")
    if total_errors == 0:
        print("🎉 All markdown links are valid!")
        sys.exit(0)
    else:
        print(f"⚠️ Found {total_errors} broken links.")
        sys.exit(1)


if __name__ == '__main__':
    main()
