#!/usr/bin/env python3
"""
Generate professional HTML from EXECUTIVE_SUMMARY.md
The HTML is optimized for printing to PDF from a browser.
"""

import markdown2
from pathlib import Path
from datetime import datetime

# Read the markdown file
md_file = Path("EXECUTIVE_SUMMARY.md")
md_content = md_file.read_text()

# Convert markdown to HTML with extras
html_content = markdown2.markdown(md_content, extras=[
    'tables',
    'fenced-code-blocks',
    'break-on-newline',
    'header-ids'
])

# Create professional HTML template with print-optimized styling
html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Options Income Screener - Executive Summary</title>
    <style>
        /* Screen styles */
        @media screen {{
            body {{
                max-width: 900px;
                margin: 40px auto;
                padding: 0 20px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
                font-size: 16px;
                line-height: 1.6;
                color: #333;
                background-color: #f5f5f5;
            }}

            .container {{
                background: white;
                padding: 60px;
                box-shadow: 0 0 20px rgba(0,0,0,0.1);
                border-radius: 8px;
            }}

            .print-instructions {{
                background: #e3f2fd;
                border-left: 4px solid #2196F3;
                padding: 20px;
                margin-bottom: 30px;
                border-radius: 4px;
            }}

            .print-instructions h3 {{
                margin-top: 0;
                color: #1976D2;
            }}

            .print-instructions code {{
                background: #fff;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
            }}
        }}

        /* Print styles */
        @media print {{
            body {{
                margin: 0;
                padding: 0;
                font-size: 11pt;
            }}

            .container {{
                padding: 0;
                box-shadow: none;
                background: white;
            }}

            .print-instructions {{
                display: none;
            }}

            @page {{
                size: letter;
                margin: 0.75in;
            }}

            h1, h2, h3, h4, h5, h6 {{
                page-break-after: avoid;
            }}

            table, pre, blockquote {{
                page-break-inside: avoid;
            }}

            img {{
                max-width: 100%;
                page-break-inside: avoid;
            }}
        }}

        /* Common styles */
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }}

        h1 {{
            color: #1a1a1a;
            font-size: 28px;
            font-weight: 700;
            margin: 30px 0 20px 0;
            padding-bottom: 10px;
            border-bottom: 3px solid #0066cc;
        }}

        h1:first-of-type {{
            margin-top: 0;
        }}

        h2 {{
            color: #0066cc;
            font-size: 22px;
            font-weight: 700;
            margin: 28px 0 16px 0;
        }}

        h3 {{
            color: #333;
            font-size: 18px;
            font-weight: 600;
            margin: 22px 0 12px 0;
        }}

        h4 {{
            color: #555;
            font-size: 16px;
            font-weight: 600;
            margin: 18px 0 10px 0;
        }}

        p {{
            margin: 12px 0;
            text-align: justify;
        }}

        ul, ol {{
            margin: 12px 0;
            padding-left: 30px;
        }}

        li {{
            margin: 6px 0;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 14px;
        }}

        th {{
            background-color: #0066cc;
            color: white;
            font-weight: 600;
            padding: 12px;
            text-align: left;
            border: 1px solid #0066cc;
        }}

        td {{
            padding: 10px 12px;
            border: 1px solid #ddd;
        }}

        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}

        code {{
            background-color: #f5f5f5;
            padding: 2px 6px;
            font-family: 'Courier New', 'Consolas', monospace;
            font-size: 0.9em;
            border-radius: 3px;
            color: #c7254e;
        }}

        pre {{
            background-color: #f5f5f5;
            padding: 16px;
            border-left: 4px solid #0066cc;
            overflow-x: auto;
            font-family: 'Courier New', 'Consolas', monospace;
            font-size: 13px;
            line-height: 1.5;
            border-radius: 4px;
            margin: 20px 0;
        }}

        pre code {{
            background-color: transparent;
            padding: 0;
            color: inherit;
        }}

        blockquote {{
            margin: 20px 0;
            padding: 15px 20px;
            background-color: #f9f9f9;
            border-left: 5px solid #0066cc;
            font-style: italic;
        }}

        hr {{
            border: none;
            border-top: 2px solid #e0e0e0;
            margin: 30px 0;
        }}

        strong {{
            font-weight: 700;
            color: #1a1a1a;
        }}

        em {{
            font-style: italic;
        }}

        a {{
            color: #0066cc;
            text-decoration: none;
        }}

        a:hover {{
            text-decoration: underline;
        }}

        /* Checkmarks */
        li strong:first-child {{
            color: #0066cc;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="print-instructions">
            <h3>📄 Print to PDF Instructions</h3>
            <p><strong>To save this document as a PDF:</strong></p>
            <ol>
                <li>Press <code>Ctrl+P</code> (Windows/Linux) or <code>Cmd+P</code> (Mac)</li>
                <li>Select "Save as PDF" or "Print to PDF" as the destination</li>
                <li>Adjust settings if needed:
                    <ul>
                        <li>Paper size: Letter (8.5 × 11 inches)</li>
                        <li>Margins: Default</li>
                        <li>Scale: 100%</li>
                    </ul>
                </li>
                <li>Click "Save" or "Print"</li>
            </ol>
            <p><em>The print instructions will not appear in the PDF.</em></p>
        </div>

        {html_content}

        <hr style="margin-top: 60px;">
        <p style="text-align: center; color: #666; font-size: 12px;">
            <em>Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</em>
        </p>
    </div>
</body>
</html>
"""

# Write HTML file
output_file = "EXECUTIVE_SUMMARY.html"
Path(output_file).write_text(html_template)

print(f"✓ HTML file generated successfully: {output_file}")
print(f"  File size: {Path(output_file).stat().st_size / 1024:.1f} KB")
print()
print("📄 To create a PDF:")
print("   1. Open EXECUTIVE_SUMMARY.html in your web browser")
print("   2. Press Ctrl+P (or Cmd+P on Mac)")
print("   3. Select 'Save as PDF' as the destination")
print("   4. Click Save")
print()
print("The HTML file is optimized for professional PDF output with:")
print("  ✓ Proper page breaks")
print("  ✓ Professional typography")
print("  ✓ Table of contents ready")
print("  ✓ Print-friendly styling")
