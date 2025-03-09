#!/usr/bin/env python3
import os
import subprocess
import sys
import re
import docx
from bs4 import BeautifulSoup, NavigableString
from jinja2 import Environment, FileSystemLoader

###############################################################################
# 1) Hard-coded summary data (first table and mid-paragraph only)
###############################################################################
def extract_summary_tables(docx_file):
    """
    Returns a hard-coded dictionary with summary data.
    Only the first summary table (Term/Meaning) and the mid-paragraph are hard-coded.
    """
    table1 = [
        ["Term", "Meaning"],
        ["Serviceable", "Meets the needs and ready to use without major issue"],
        ["Unserviceable", "Not ready to use for various reasons"],
        ["Safety", "Dangerous in some way or could cause harm or injury"],
        ["Maintenance", "Needs routine or ongoing maintenance"],
        ["NA", "Not applicable"]
    ]
    mid_paragraph = (
        "These terms are for the summary only and anything found defective "
        "will have a detailed explanation as well as pictures in the appropriate section."
    )
    return {
        "table1": table1,
        "mid_paragraph": mid_paragraph
    }

###############################################################################
# 2) Run Pandoc to convert DOCX to HTML (with media extraction)
###############################################################################
def run_pandoc(docx_file, temp_html, media_dir):
    cmd = ["pandoc", f"--extract-media={media_dir}", "-s", "-o", temp_html, docx_file]
    try:
        subprocess.run(cmd, check=True)
        print(f"[INFO] Pandoc conversion succeeded. Output: {temp_html}, media in '{media_dir}'")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Pandoc conversion failed: {e}")
        sys.exit(1)

###############################################################################
# 3) Parse the Pandoc-generated HTML into sections by heading tags
###############################################################################
def parse_sections_from_html(html_file):
    with open(html_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    sections = []
    current_section = {"title": "Front Matter", "blocks": []}
    body = soup.body

    for elem in body.children:
        if isinstance(elem, NavigableString):
            text_val = elem.strip()
            if text_val:
                current_section["blocks"].append({
                    "type": "text",
                    "content": text_val
                })
            continue

        if not hasattr(elem, "name"):
            continue

        if elem.name in ["h1", "h2"]:
            if current_section["blocks"] or current_section["title"] != "Front Matter":
                sections.append(current_section)
            current_section = {"title": elem.get_text(strip=True), "blocks": []}
        else:
            if hasattr(elem, "decode_contents"):
                decoded_html = elem.decode_contents()
            else:
                decoded_html = str(elem)

            if elem.name == "p":
                imgs = elem.find_all("img")
                if imgs and not elem.get_text(strip=True):
                    for img in imgs:
                        current_section["blocks"].append({
                            "type": "image",
                            "path": img.get("src")
                        })
                else:
                    current_section["blocks"].append({
                        "type": "text",
                        "content": decoded_html
                    })
            elif elem.name == "table":
                table_rows = []
                for tr in elem.find_all("tr"):
                    row_cells = [re.sub(r"\s+", " ", td.get_text()).strip() for td in tr.find_all(["th", "td"])]
                    table_rows.append(row_cells)
                current_section["blocks"].append({
                    "type": "summary-fixed-table",
                    "rows": table_rows
                })
            else:
                current_section["blocks"].append({
                    "type": "text",
                    "content": decoded_html
                })

    if current_section["blocks"] or current_section["title"]:
        sections.append(current_section)

    return sections

###############################################################################
# 4) Inject the hard-coded summary data (table1 + mid-paragraph) into the "Summary" section
#    by replacing the first summary table block.
###############################################################################
def inject_clean_summary(sections, summary_data):
    if not summary_data:
        print("[WARNING] No summary_data found. Skipping injection.")
        return sections

    for sec in sections:
        if sec["title"].lower() == "summary":
            new_blocks = []
            first_table_replaced = False
            for b in sec["blocks"]:
                if not first_table_replaced and b["type"] == "summary-fixed-table":
                    new_blocks.append({
                        "type": "summary-fixed-table",
                        "rows": summary_data["table1"]
                    })
                    if summary_data["mid_paragraph"]:
                        new_blocks.append({
                            "type": "text",
                            "content": summary_data["mid_paragraph"]
                        })
                    first_table_replaced = True
                    continue
                new_blocks.append(b)
            sec["blocks"] = new_blocks
    return sections

###############################################################################
# 5) Remove the "Front Matter" section entirely so that no text appears before the first heading.
###############################################################################
def remove_front_matter(sections):
    filtered = [sec for sec in sections if sec["title"].lower() != "front matter"]
    return filtered

###############################################################################
# 6) Render final HTML report using Jinja2
###############################################################################
def render_final_html(sections, meta, template_file, output_html):
    env = Environment(loader=FileSystemLoader(os.path.dirname(template_file) or "."))
    template = env.get_template(os.path.basename(template_file))
    data = {
        "doc_title": meta.get("doc_title", "No Title"),
        # Only the file name will be shown in the header.
        "address": meta.get("address", ""),
        "inspection_date": meta.get("inspection_date", ""),
        "inspector_name": meta.get("inspector_name", ""),
        "sections": sections
    }
    rendered = template.render(data)
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(rendered)
    print(f"[INFO] Final HTML saved to {output_html}")

###############################################################################
# 7) Extract basic document metadata (file name without extension)
###############################################################################
def extract_doc_metadata(docx_file):
    base = os.path.splitext(os.path.basename(docx_file))[0]
    return {
        "doc_title": base,
        "address": "",
        "inspection_date": "",
        "inspector_name": ""
    }

###############################################################################
# MAIN
###############################################################################
def main():
    docx_file = "sample-seller.docx"
    template_file = "report_template.html"
    output_html = "final_output.html"
    temp_html = "temp_output.html"
    media_dir = "media"

    # 1) Get hard-coded summary data (first table and mid-paragraph)
    summary_data = extract_summary_tables(docx_file)

    # 2) Run Pandoc to convert the entire DOCX to HTML (with media extraction)
    if not os.path.exists(media_dir):
        os.makedirs(media_dir)
    run_pandoc(docx_file, temp_html, media_dir)

    # 3) Parse sections from the Pandoc-generated HTML
    sections = parse_sections_from_html(temp_html)

    # 4) Inject the hard-coded summary data into the "Summary" section.
    sections = inject_clean_summary(sections, summary_data)

    # 5) Remove the "Front Matter" section completely.
    sections = remove_front_matter(sections)

    # 6) Extract basic metadata (file name without extension)
    meta = extract_doc_metadata(docx_file)

    # 7) Render the final HTML report using the provided Jinja2 template.
    render_final_html(sections, meta, template_file, output_html)

if __name__ == "__main__":
    main()
