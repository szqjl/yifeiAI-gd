#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from pathlib import Path

# Get file path from command line or use default
import sys
if len(sys.argv) > 1:
    input_file = Path(sys.argv[1])
else:
    # Find the file by listing all md files
    md_files = list(Path('docs/skill').glob('*.md'))
    # Get the one that was just created (most recent)
    input_file = max(md_files, key=lambda p: p.stat().st_mtime)

print(f'Processing: {input_file}')

# Read content
content = input_file.read_text(encoding='utf-8')
print(f'Original: {len(content)} chars, {len(content.splitlines())} lines')

# Remove base64 images
cleaned = re.sub(r'!\[\]\(data:image/[^)]+\)', '', content)

# Remove multiple empty lines
cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

# Clean lines
lines = [line.rstrip() for line in cleaned.splitlines()]

# Remove leading/trailing empty lines
while lines and not lines[0].strip():
    lines.pop(0)
while lines and not lines[-1].strip():
    lines.pop(-1)

# Join back
cleaned_content = '\n'.join(lines)

# Save
output = input_file.with_name(f'{input_file.stem}_cleaned.md')
output.write_text(cleaned_content, encoding='utf-8')

print(f'Cleaned: {len(cleaned_content)} chars, {len(cleaned_content.splitlines())} lines')
print(f'Removed: {len(content) - len(cleaned_content)} chars')
print(f'Saved: {output}')
