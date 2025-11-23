#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Convert docx files to markdown using markitdown"""

from markitdown import MarkItDown
import os
from pathlib import Path

def convert_docx_to_markdown(docx_path, output_dir=None):
    """Convert docx file to markdown"""
    docx_path = Path(docx_path)
    
    if not docx_path.exists():
        print(f"Error: File not found - {docx_path}")
        return None
    
    print(f"Converting: {docx_path}")
    
    try:
        # Use markitdown to convert
        md = MarkItDown()
        result = md.convert(str(docx_path))
        
        # Determine output path
        if output_dir is None:
            output_dir = docx_path.parent
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate output filename
        output_file = output_dir / f"{docx_path.stem}.md"
        
        # Save markdown file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result.markdown)
        
        print(f"Success!")
        print(f"  Input: {docx_path}")
        print(f"  Output: {output_file}")
        print(f"  Size: {len(result.markdown)} characters")
        
        return output_file
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Convert docx file in project
    docx_file = "docs/skill/Þèµ°¼¼ÇÉÃØ¼®(¶¡»ª) .docx"
    
    if os.path.exists(docx_file):
        convert_docx_to_markdown(docx_file)
    else:
        print(f"File not found: {docx_file}")
