from docx.shared import Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def add_grey_horizontal_line(doc):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)

    p_elm = p._p
    p_pr = p_elm.get_or_add_pPr()

    p_borders = OxmlElement('w:pBdr')

    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '6')        # thin line
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), 'BFBFBF')  # grey

    p_borders.append(bottom)
    p_pr.append(p_borders)

    return p
# -----------------------------------------------


# ---------------- UTILITY ----------------
def normalize_list(items):
    if not items:
        return ["None"]
    cleaned = [i.strip() for i in items if i.strip()]
    return cleaned if cleaned else ["None"]