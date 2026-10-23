"""Rebrand the Training/ phase decks to the Noveti Drone Academy identity.

Reads the originals from Training/ and writes the rebranded copies to
Training/noveti/ -- the originals are never modified. Only colours, fonts,
the deck eyebrow/footer names and the logo change; slide content and layout
stay as authored.

    python Training/noveti/rebrand_pptx.py
"""
import pathlib
import re
import zipfile

from PIL import Image

HERE = pathlib.Path(__file__).parent
SRC = HERE.parent
BRAND = HERE / "brand"
LOCKUP = BRAND / "noveti-drone-academy-on-light.png"
MARK = BRAND / "noveti-mark.png"

HEADING_FONT = "Century Gothic"  # Office-bundled geometric stand-in for Poppins
BODY_FONT = "Calibri"
TITLE_MIN_SZ = 2400  # runs at or above this size are treated as titles

# Old teal palette -> Noveti blues. Semantic accents (orange, green, red) stay.
COLORS = {
    "1BC7C7": "2563EB", "4FD8D8": "60A5FA", "182033": "0B1B33",
    "F3FAFA": "EEF4FF", "D7EDEE": "DBEAFE", "556070": "475569",
    "8DB9FF": "93C5FD",
}

DECKS = [f"Hula_Drone_Training_Phase_{n}_High_Level.pptx" for n in (1, 2, 3)]
EMU = 914400  # per inch


def pic(rid, pid, name, x, y, w, h):
    x, y, w, h = (int(v * EMU) for v in (x, y, w, h))
    return (
        f'<p:pic><p:nvPicPr><p:cNvPr id="{pid}" name="{name}" descr="Noveti Drone Academy"/>'
        '<p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>'
        f'<p:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>'
        f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>'
    )


def recolor(xml):
    for old, new in COLORS.items():
        xml = re.sub(f'val="{old}"', f'val="{new}"', xml, flags=re.I)
    return xml


def fonts(xml):
    xml = xml.replace('typeface="Aptos"', f'typeface="{BODY_FONT}"')

    def title_run(m):
        rpr = m.group(0)
        sz = re.search(r'sz="(\d+)"', rpr)
        if not sz or int(sz.group(1)) < TITLE_MIN_SZ:
            return rpr
        latin = f'<a:latin typeface="{HEADING_FONT}"/>'
        if "<a:latin " in rpr:
            return re.sub(r'<a:latin typeface="[^"]*"', f'<a:latin typeface="{HEADING_FONT}"', rpr)
        if rpr.endswith("/>"):
            return rpr[:-2] + f">{latin}</a:rPr>"
        for tag in ("<a:ea ", "<a:cs ", "<a:sym ", "<a:hlinkClick", "</a:rPr>"):
            if tag in rpr:
                return rpr.replace(tag, latin + tag, 1)
        return rpr

    return re.sub(r"<a:rPr\b[^>]*?(?:/>|>.*?</a:rPr>)", title_run, xml, flags=re.S)


def next_rid(rels):
    return f"rId{max((int(i) for i in re.findall(r'Id=\"rId(\d+)\"', rels)), default=0) + 1}"


def add_rel(rels, rid, target):
    rel = (f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
           f'relationships/image" Target="{target}"/>')
    return rels.replace("</Relationships>", rel + "</Relationships>")


def rebrand(name):
    out = HERE / name.replace("Hula_Drone", "Noveti_Hula_Drone")
    with zipfile.ZipFile(SRC / name) as zin:
        parts = {i.filename: zin.read(i.filename) for i in zin.infolist()}

    def text(p):
        return parts[p].decode("utf8")

    parts["ppt/media/noveti-lockup.png"] = LOCKUP.read_bytes()
    parts["ppt/media/noveti-mark.png"] = MARK.read_bytes()
    lw, lh = Image.open(LOCKUP).size

    theme = text("ppt/theme/theme1.xml")
    theme = re.sub(r'(<a:majorFont><a:latin typeface=")[^"]*', r"\1" + HEADING_FONT, theme)
    theme = re.sub(r'(<a:minorFont><a:latin typeface=")[^"]*', r"\1" + BODY_FONT, theme)
    parts["ppt/theme/theme1.xml"] = recolor(theme).encode("utf8")

    for p in sorted(x for x in parts if re.match(r"ppt/slides/slide\d+\.xml$", x)):
        x = fonts(recolor(text(p)))
        x = x.replace("<a:t>HULA DRONE TRAINING</a:t>", "<a:t>NOVETI DRONE ACADEMY · HULA DRONE TRAINING</a:t>")
        x = re.sub(r"<a:t>(Phase \d)</a:t>", r"<a:t>Noveti Drone Academy · \1</a:t>", x)

        relp = p.replace("slides/", "slides/_rels/") + ".rels"
        rels = text(relp)
        pid = max(int(i) for i in re.findall(r'<p:cNvPr id="(\d+)"', x)) + 1
        rid = next_rid(rels)
        rels = add_rel(rels, rid, "../media/noveti-mark.png")
        # Small N mark beside the footer text, on every slide.
        shapes = pic(rid, pid, "Noveti mark", 0.24, 7.06, 0.3, 0.3)
        if p.endswith("/slide1.xml"):
            rid2 = next_rid(rels)
            rels = add_rel(rels, rid2, "../media/noveti-lockup.png")
            h = 0.75
            shapes += pic(rid2, pid + 1, "Noveti Drone Academy logo", 0.65, 5.85, h * lw / lh, h)
        x = x.replace("</p:spTree>", shapes + "</p:spTree>", 1)
        parts[p] = x.encode("utf8")
        parts[relp] = rels.encode("utf8")

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for p, data in parts.items():
            zout.writestr(p, data)
    print("wrote", out.relative_to(SRC.parent))


if __name__ == "__main__":
    for deck in DECKS:
        rebrand(deck)
