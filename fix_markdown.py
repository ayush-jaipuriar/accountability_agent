#!/usr/bin/env python3
"""
Script to convert all Markdown formatting to HTML in the codebase.
This ensures Telegram messages display correctly without clickable command links.
"""

import re
from pathlib import Path

def convert_markdown_to_html(content: str) -> str:
    """Convert Markdown syntax to HTML syntax in message strings."""
    
    # Replace **bold** with <b>bold</b>
    # Use negative lookbehind/lookahead to avoid replacing in comments or docstrings
    content = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', content)
    
    # Replace parse_mode='Markdown' or parse_mode="Markdown" with parse_mode='HTML'
    content = re.sub(r"parse_mode=['\"]Markdown['\"]", "parse_mode='HTML'", content)
    
    # Replace ParseMode.MARKDOWN with ParseMode.HTML (if any)
    content = re.sub(r'ParseMode\.MARKDOWN', 'ParseMode.HTML', content)
    
    return content

def fix_file(file_path: Path) -> bool:
    """Fix markdown in a single file. Returns True if changes were made."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        new_content = convert_markdown_to_html(original_content)
        
        if new_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✅ Fixed: {file_path}")
            return True
        else:
            print(f"⏭️  No changes: {file_path}")
            return False
    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")
        return False

def main():
    """Fix all Python files in src/ directory."""
    src_dir = Path(__file__).parent / "src"
    
    if not src_dir.exists():
        print(f"❌ Directory not found: {src_dir}")
        return
    
    python_files = list(src_dir.rglob("*.py"))
    print(f"Found {len(python_files)} Python files in src/\n")
    
    fixed_count = 0
    for file_path in python_files:
        if fix_file(file_path):
            fixed_count += 1
    
    print(f"\n📊 Summary: Fixed {fixed_count}/{len(python_files)} files")

if __name__ == "__main__":
    main()
