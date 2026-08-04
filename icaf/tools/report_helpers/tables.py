from docx.shared import RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.table import WD_TABLE_ALIGNMENT


def style_table_header(cell, bg_color="1F4E79"):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), bg_color)
    tc_pr.append(shd)

    for paragraph in cell.paragraphs:
        for run in paragraph.runs:
            run.font.bold = True
            run.font.color.rgb = RGBColor(255, 255, 255)


def prevent_table_row_split(table):
    for row in table.rows:
        tr = row._tr
        trPr = tr.get_or_add_trPr()
        cantSplit = OxmlElement("w:cantSplit")
        trPr.append(cantSplit)


def add_two_column_table(doc,data):

    table = doc.add_table(rows=len(data),cols=2)

    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    for i,(key,val) in enumerate(data):

        table.rows[i].cells[0].text = key
        table.rows[i].cells[1].text = str(val)

    return table