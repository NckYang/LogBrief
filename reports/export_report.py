"""Export Markdown to Word and printable HTML. Requires python-docx==1.2.0."""
from pathlib import Path
import argparse
import html
import re
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parent


def plain(text):
    text = re.sub(r'\[([^]]+)\]\(([^)]+)\)', r'\1 (\2)', text)
    return text.replace('**', '').replace('`', '')


def font(style, size, name='Calibri'):
    style.font.name = name
    style.font.size = Pt(size)
    style.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'), 'Microsoft JhengHei')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-stem', default='LogBrief_HW2_Report')
    args = parser.parse_args()
    if Path(args.output_stem).name != args.output_stem:
        raise ValueError('output-stem must be a filename without directories')
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin = section.bottom_margin = Cm(2)
    section.left_margin = section.right_margin = Cm(2.1)
    font(doc.styles['Normal'], 10.5)
    doc.styles['Normal'].paragraph_format.line_spacing = 1.25
    doc.styles['Normal'].paragraph_format.space_after = Pt(6)
    for name, size in [('Title', 22), ('Heading 1', 16), ('Heading 2', 12)]:
        font(doc.styles[name], size)
        doc.styles[name].font.color.rgb = RGBColor.from_string('17365D')
    font(doc.styles['No Spacing'], 8.5, 'Consolas')
    footer = section.footer.paragraphs[0]
    footer.alignment = 2
    footer.add_run('LogBrief | HW2 | ')
    field = OxmlElement('w:fldSimple')
    field.set(qn('w:instr'), 'PAGE')
    footer._p.append(field)
    doc.core_properties.title = 'LogBrief — HW2 AI-Assisted Programming Project'
    doc.core_properties.subject = '專案目的、AI 協作、軟體工程與實驗驗證'
    doc.core_properties.author = '楊竣凱'
    lines = (ROOT / 'LogBrief_HW2_Report.md').read_text(encoding='utf-8-sig').splitlines()
    web = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith('```'):
            block = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                block.append(lines[i])
                i += 1
            for row in block:
                p = doc.add_paragraph(row, style='No Spacing')
                p.paragraph_format.keep_with_next = False
            web.append('<pre>' + html.escape('\n'.join(block)) + '</pre>')
        elif line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                cells = [plain(c.strip()) for c in lines[i].strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?', c) for c in cells):
                    rows.append(cells)
                i += 1
            table = doc.add_table(rows=1, cols=len(rows[0]))
            table.style = 'Light Shading Accent 1'
            for j, cell in enumerate(rows[0]):
                table.rows[0].cells[j].text = cell
            header = OxmlElement('w:tblHeader')
            table.rows[0]._tr.get_or_add_trPr().append(header)
            for row in rows[1:]:
                cells = table.add_row().cells
                for j, cell in enumerate(row):
                    cells[j].text = cell
            for row in table.rows:
                cant = OxmlElement('w:cantSplit')
                row._tr.get_or_add_trPr().append(cant)
                for cell in row.cells:
                    for p in cell.paragraphs:
                        p.paragraph_format.space_after = Pt(4)
                        for run in p.runs:
                            run.font.size = Pt(9)
            web.append('<table>' + ''.join('<tr>' + ''.join(
                f'<{"th" if n == 0 else "td"}>' + html.escape(c) + f'</{"th" if n == 0 else "td"}>'
                for c in row) + '</tr>' for n, row in enumerate(rows)) + '</table>')
            continue
        elif line.startswith('# '):
            doc.add_heading(plain(line[2:]), 0)
            web.append('<h1>' + html.escape(plain(line[2:])) + '</h1>')
        elif line.startswith('## '):
            doc.add_heading(plain(line[3:]), 1)
            web.append('<h2>' + html.escape(plain(line[3:])) + '</h2>')
        elif line.startswith('### '):
            doc.add_heading(plain(line[4:]), 2)
            web.append('<h3>' + html.escape(plain(line[4:])) + '</h3>')
        else:
            doc.add_paragraph(plain(line))
            web.append('<p>' + html.escape(plain(line)) + '</p>')
        i += 1
    doc.save(ROOT / (args.output_stem + '.docx'))
    css = '''body{font-family:"Microsoft JhengHei",sans-serif;max-width:900px;margin:40px auto;color:#202830;line-height:1.65}
    h1,h2,h3{color:#17365d;break-after:avoid}table{border-collapse:collapse;width:100%;font-size:90%;margin:16px 0}
    th,td{border:1px solid #cbd5e1;padding:7px;vertical-align:top}th{background:#edf2f7}tr{break-inside:avoid}
    pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f5f7;padding:12px;font-size:85%}p{overflow-wrap:anywhere}
    @page{size:A4;margin:20mm} @media print{body{margin:0;max-width:none;font-size:10.5pt}}'''
    (ROOT / (args.output_stem + '.html')).write_text(
        '<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>LogBrief HW2 報告</title><style>'
        + css + '</style><body>' + '\n'.join(web) + '</body></html>', encoding='utf-8')
    print('Exported Word and HTML report.')


if __name__ == '__main__':
    main()
