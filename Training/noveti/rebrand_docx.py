"""Rebrand the Training/ Word documents to the Noveti Drone Academy identity.

Reads the originals from Training/ and writes the rebranded copies to
Training/noveti/ -- the originals are never modified. Edits are made on the
raw OOXML (colours, heading font, names, logo), so content and layout stay
exactly as authored.

    python Training/noveti/rebrand_docx.py
"""
import pathlib
import re
import shutil
import zipfile

from PIL import Image

HERE = pathlib.Path(__file__).parent
SRC = HERE.parent
BRAND = HERE / "brand"
LOGO = BRAND / "noveti-drone-academy-on-light.png"

HEADING_FONT = "Century Gothic"  # Office-bundled geometric stand-in for Poppins
BODY_FONT = "Calibri"

# Old palette -> Noveti palette (navy #0B1B33, blue #2563EB, deep blue #1E3A8A).
COLORS = {
    "1B1F2A": "0B1B33", "2B2B2B": "1E293B", "1F3864": "0B1B33",
    "D94E2A": "2563EB", "D6521A": "2563EB", "C55A11": "0369A1",
    "2E75B6": "1E3A8A", "2E8B57": "2563EB", "3A7C22": "2563EB",
    "2E5B4C": "1E3A8A", "2E74B5": "1E3A8A", "F4F1EC": "EEF4FF",
    "5B6472": "475569", "5A5A5A": "475569", "595959": "475569",
}

DOCS = {
    "Hula_Drone_Academy_Brochure.docx": {
        "text": {"HULA DRONE ACADEMY": "NOVETI DRONE ACADEMY",
                 "Hula Drone Academy · Program Overview": "Noveti Drone Academy · Program Overview"},
        "logo_top_cm": 7.0, "body_font": False, "center": True,
    },
    "Hula_Drone_5_Session_Intro_Plan.docx": {
        # The logo carries the academy name, so the plan's own title becomes the headline.
        "text": {'<w:t xml:space="preserve">Hula Drone Academy</w:t></w:r></w:p>': "</w:r></w:p>",
                 '<w:sz w:val="30"/><w:szCs w:val="30"/></w:rPr><w:t xml:space="preserve">5-Session':
                 '<w:b/><w:color w:val="0B1B33"/><w:sz w:val="44"/><w:szCs w:val="44"/></w:rPr>'
                 '<w:t xml:space="preserve">5-Session'},
        "logo_top_cm": 5.0, "body_font": True,
    },
    "Hula_Drone_Intro_Pilot_Proposal.docx": {
        "text": {"HULA DRONE CODING — INTRO SESSION PROPOSAL": "NOVETI DRONE ACADEMY — INTRO SESSION PROPOSAL"},
        "logo_top_cm": 5.0, "body_font": True,
    },
    "Hula_Drone_Intro_Pilot_Proposal_AR.docx": {
        "text": {"برمجة درون هولا — اقتراح حصص تعريفية": "أكاديمية نوفيتي للدرون — اقتراح حصص تعريفية"},
        "logo_top_cm": 5.0, "body_font": False, "rtl": True,
    },
    "Hula_Drone_Course_Plan.docx": {
        "text": {">Hula Drone Training </w:t>": ">Noveti Drone Academy  |  Hula Drone Training </w:t>"},
        "header_logo": "media/image1.png", "body_font": False,
    },
}

EMU_PER_CM = 360000


def inline_logo(rid, width_cm, rtl=False, center=False):
    w, h = Image.open(LOGO).size
    cx = int(width_cm * EMU_PER_CM)
    cy = int(cx * h / w)
    jc = "center" if center else "right" if rtl else "left"
    return (
        f'<w:p><w:pPr><w:spacing w:after="240"/><w:jc w:val="{jc}"/></w:pPr><w:r><w:drawing>'
        f'<wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/>'
        f'<wp:docPr id="9001" name="Noveti Drone Academy logo" descr="Noveti Drone Academy"/>'
        '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:nvPicPr><pic:cNvPr id="9001" name="noveti-logo.png"/><pic:cNvPicPr/></pic:nvPicPr>'
        f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic>'
        '</wp:inline></w:drawing></w:r></w:p>'
    )


def recolor(xml):
    for old, new in COLORS.items():
        xml = re.sub(f'"{old}"', f'"{new}"', xml, flags=re.I)
    return xml


def heading_fonts(styles, body_font):
    """Point Title/Heading styles at the heading font; optionally set the body default."""
    font = f'<w:rFonts w:ascii="{HEADING_FONT}" w:hAnsi="{HEADING_FONT}"/>'

    def fix_style(m):
        block = m.group(0)
        block = re.sub(r"<w:rFonts [^>]*/>", "", block)
        if "<w:rPr>" in block:
            return block.replace("<w:rPr>", "<w:rPr>" + font, 1)
        if "<w:rPr/>" in block:
            return block.replace("<w:rPr/>", f"<w:rPr>{font}</w:rPr>", 1)
        return block.replace("</w:style>", f"<w:rPr>{font}</w:rPr></w:style>")

    styles = re.sub(r'<w:style [^>]*w:styleId="(Title|Heading[1-3])".*?</w:style>', fix_style, styles, flags=re.S)
    if body_font:
        body = f'<w:rFonts w:ascii="{BODY_FONT}" w:hAnsi="{BODY_FONT}" w:eastAsia="{BODY_FONT}" w:cs="{BODY_FONT}"/>'
        if "<w:rPrDefault/>" in styles:
            styles = styles.replace("<w:rPrDefault/>", f"<w:rPrDefault><w:rPr>{body}</w:rPr></w:rPrDefault>", 1)
        elif "<w:rPrDefault>" in styles:
            styles = re.sub(r"(<w:rPrDefault>\s*<w:rPr>)(?:<w:rFonts [^>]*/>)?", r"\1" + body, styles, count=1)
        else:
            styles = re.sub(r"<w:docDefaults>", f"<w:docDefaults><w:rPrDefault><w:rPr>{body}</w:rPr></w:rPrDefault>",
                            styles, count=1)
    return styles


def heading_runs(doc):
    """Direct run fonts on heading/title paragraphs would override the style, so swap them too."""
    def fix_para(m):
        p = m.group(0)
        if re.search(r'w:pStyle w:val="(Title|Heading[1-3])"', p) or re.search(r'w:sz w:val="(4[0-9]|5[0-9]|6[0-9])"', p):
            p = re.sub(r'w:ascii="[^"]*"', f'w:ascii="{HEADING_FONT}"', p)
            p = re.sub(r'w:hAnsi="[^"]*"', f'w:hAnsi="{HEADING_FONT}"', p)
            if "<w:rFonts" not in p:
                p = p.replace("<w:rPr>", f'<w:rPr><w:rFonts w:ascii="{HEADING_FONT}" w:hAnsi="{HEADING_FONT}"/>')
        return p
    return re.sub(r"<w:p[ >].*?</w:p>", fix_para, doc, flags=re.S)


def add_image_rel(rels, target):
    ids = [int(i) for i in re.findall(r'Id="rId(\d+)"', rels)]
    rid = f"rId{max(ids, default=0) + 1}"
    rel = (f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
           f'relationships/image" Target="{target}"/>')
    return rels.replace("</Relationships>", rel + "</Relationships>"), rid


def ensure_png(ct):
    if 'Extension="png"' not in ct:
        ct = ct.replace("<Default ", '<Default Extension="png" ContentType="image/png"/><Default ', 1)
    return ct


def rebrand(name, cfg):
    src = SRC / name
    out = HERE / name.replace("Hula_Drone", "Noveti_Hula_Drone")
    with zipfile.ZipFile(src) as zin:
        parts = {i.filename: zin.read(i.filename) for i in zin.infolist()}

    def text(p):
        return parts[p].decode("utf8")

    for p in list(parts):
        if re.match(r"word/(document|header\d*|footer\d*|styles|numbering)\.xml$", p):
            x = recolor(text(p))
            for old, new in cfg["text"].items():
                x = x.replace(old, new)
            parts[p] = x.encode("utf8")

    parts["word/styles.xml"] = heading_fonts(text("word/styles.xml"), cfg["body_font"]).encode("utf8")
    parts["word/document.xml"] = heading_runs(text("word/document.xml")).encode("utf8")

    logo = LOGO.read_bytes()
    if "logo_top_cm" in cfg:
        parts["word/media/noveti-logo.png"] = logo
        rels, rid = add_image_rel(text("word/_rels/document.xml.rels"), "media/noveti-logo.png")
        parts["word/_rels/document.xml.rels"] = rels.encode("utf8")
        doc = text("word/document.xml")
        doc = doc.replace("<w:body>", "<w:body>" + inline_logo(rid, cfg["logo_top_cm"], cfg.get("rtl", False), cfg.get("center", False)), 1)
        parts["word/document.xml"] = doc.encode("utf8")
        parts["[Content_Types].xml"] = ensure_png(text("[Content_Types].xml")).encode("utf8")
    if "header_logo" in cfg:
        # Swap the header's product logo for the Noveti lockup, keeping its width
        # so it still clears the header title beside it.
        parts["word/" + cfg["header_logo"]] = logo
        hdr = text("word/header1.xml")
        w, h = Image.open(LOGO).size
        m = re.search(r'<wp:extent cx="(\d+)" cy="(\d+)"/>', hdr)
        cx = int(m.group(1))
        cy = int(cx * h / w)
        hdr = hdr.replace(f'cx="{cx}" cy="{m.group(2)}"', f'cx="{cx}" cy="{cy}"')
        parts["word/header1.xml"] = hdr.encode("utf8")

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for p, data in parts.items():
            zout.writestr(p, data)
    print("wrote", out.relative_to(SRC.parent))


if __name__ == "__main__":
    for name, cfg in DOCS.items():
        rebrand(name, cfg)
