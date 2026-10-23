"""Builds the Noveti Drone Academy lockups from the flat N mark (noveti-mark-flat.svg, rendered to noveti-mark.png)."""
import pathlib
from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).parent
NAVY, BLUE, SKY, WHITE = "#0B1B33", "#2563EB", "#60A5FA", "#FFFFFF"
mark = Image.open(HERE / "noveti-mark.png").convert("RGBA")
bold = ImageFont.truetype(str(HERE / "fonts/Poppins-ExtraBold.ttf"), 300)
sub = ImageFont.truetype(str(HERE / "fonts/Poppins-Bold.ttf"), 112)

def spaced(draw, xy, text, font, fill, track):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + track
    return x

def lockup(name, word, accent):
    m = mark.resize((560, 560), Image.LANCZOS)
    img = Image.new("RGBA", (2600, 620), (0, 0, 0, 0))
    img.alpha_composite(m, (20, 30))
    d = ImageDraw.Draw(img)
    d.text((660, 20), "Noveti", font=bold, fill=word)
    right = spaced(d, (668, 400), "DRONE ACADEMY", sub, accent, 18)
    img = img.crop((0, 0, int(max(right, 660 + d.textlength("Noveti", font=bold))) + 30, 620))
    img.save(HERE / name)
    print(name, img.size)

lockup("noveti-drone-academy-on-light.png", NAVY, BLUE)
lockup("noveti-drone-academy-on-dark.png", WHITE, SKY)
