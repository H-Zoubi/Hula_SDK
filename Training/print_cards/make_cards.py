"""Build Hula_Print_Cards.pdf: QR codes 0-9, number labels 0-9 and arrow labels on A4.

Proportions are measured from a straightened photo of the kit's QR card and
from the label cards pictured in the Hula user manual (pp. 81-82). QR patterns
follow Qr5x5Concave::QrEncode in the drone firmware (v1.9.0.9.1.1.7.3). Test the
cards on the drone before printing a full set.

Usage: python make_cards.py
"""
from pathlib import Path

import pymupdf

CM = 72 / 2.54
PAGE_W, PAGE_H = pymupdf.paper_size("a4")
CARD = 20 * CM  # change to match the kit card
BLACK = (0, 0, 0)
WHITE = (1, 1, 1)
FONT_FILE = "C:/Windows/Fonts/arialbd.ttf"
FONT = pymupdf.Font(fontfile=FONT_FILE)
DIGIT_HEIGHT = 0.716  # Arial digit height, as a fraction of the font size
# The large label digits are thinner and rounder than Arial Bold.
LABEL_FONT_FILE = "C:/Windows/Fonts/seguisb.ttf"
LABEL_FONT = pymupdf.Font(fontfile=LABEL_FONT_FILE)
LABEL_FONT_DIGIT_HEIGHT = 0.7
OUTPUT = Path(__file__).with_name("Hula_Print_Cards.pdf")

# QR card, as fractions of the card's width.
QR_SQUARE = 1 / 1.3
QR_CAPTION_HEIGHT = 0.04
QR_CAPTION_ARROW = 0.035

# Label cards, as fractions of the card's width.
FRAME = 0.095
NOTCH = 0.2
LABEL_DIGIT_HEIGHT = 0.67
LABEL_CAPTION_HEIGHT = 0.04
LABEL_CAPTION_ARROW = 0.035
LABEL_CAPTION_ARROW_X = 0.3  # distance of each small arrow from the centre

# Points of an up arrow as fractions of its height, around its centre.
ARROW = [(0, -0.5), (0.31, 0.04), (0.11, 0.04), (0.11, 0.5), (-0.11, 0.5), (-0.11, 0.04), (-0.31, 0.04)]
ARROW_HEIGHT = 0.58  # large arrow on an arrow card, as a fraction of the card's width
ROTATIONS = {"UP": 0, "RIGHT": 90, "DOWN": 180, "LEFT": 270}


def qr_pattern(qr_id):
    """The 8x8 grid for a QR id (0-2047), as rows where "#" is black."""
    bit = [(qr_id >> k) & 1 for k in range(11)]
    odd_check = lambda *bits: 1 - sum(bit[k] for k in bits) % 2
    # 1 is white. The black border, white ring and top mark never change.
    data = [
        [bit[0], bit[1], 1 - bit[1], bit[2]],
        [odd_check(0, 5, 8), bit[3], bit[4], odd_check(2, 7, 10)],
        [bit[5], odd_check(3, 4, 6), bit[6], bit[7]],
        [bit[8], bit[9], odd_check(8, 9, 10), bit[10]],
    ]
    rows = ["#" * 8, "#..##..#"]
    rows += ["#." + "".join("." if v else "#" for v in row) + ".#" for row in data]
    rows += ["#......#", "#" * 8]
    return rows


def card_rect():
    left, top = (PAGE_W - CARD) / 2, (PAGE_H - CARD) / 2
    return pymupdf.Rect(left, top, left + CARD, top + CARD)


def text(page, centre_x, centre_y, value, height, color=BLACK):
    """Draw digits centred on a point, given their height in points."""
    size = height / DIGIT_HEIGHT
    width = FONT.text_length(value, fontsize=size)
    page.insert_text(
        (centre_x - width / 2, centre_y + height / 2), value,
        fontsize=size, fontname="arialbd", fontfile=FONT_FILE, color=color,
    )


def label_digit(page, number):
    height = CARD * LABEL_DIGIT_HEIGHT
    size = height / LABEL_FONT_DIGIT_HEIGHT
    width = LABEL_FONT.text_length(str(number), fontsize=size)
    page.insert_text(
        (PAGE_W / 2 - width / 2, PAGE_H / 2 + height / 2), str(number),
        fontsize=size, fontname="seguisb", fontfile=LABEL_FONT_FILE, color=BLACK,
    )


def draw_arrow(page, centre, height, degrees, color=BLACK):
    matrix = pymupdf.Matrix(degrees)
    points = [pymupdf.Point(x * height, y * height) * matrix + centre for x, y in ARROW]
    page.draw_polyline(points + [points[0]], color=None, fill=color, closePath=True)


def caption(page, y, value, arrow_x, text_height, arrow_height, color):
    """The kit's caption: a small up arrow, the two-digit number, a small up arrow."""
    text(page, PAGE_W / 2, y, value, text_height, color)
    for x in (PAGE_W / 2 - arrow_x, PAGE_W / 2 + arrow_x):
        draw_arrow(page, pymupdf.Point(x, y), arrow_height, 0, color)


def qr_card(doc, qr_id):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    card = card_rect()
    side = CARD * QR_SQUARE
    square = pymupdf.Rect(PAGE_W / 2 - side / 2, PAGE_H / 2 - side / 2, PAGE_W / 2 + side / 2, PAGE_H / 2 + side / 2)
    pattern = qr_pattern(qr_id)
    cell = side / len(pattern)
    # One shape, so no hairlines show between neighbouring black squares.
    shape = page.new_shape()
    for r, row in enumerate(pattern):
        for c, value in enumerate(row):
            if value == "#":
                x, y = square.x0 + c * cell, square.y0 + r * cell
                shape.draw_rect(pymupdf.Rect(x, y, x + cell, y + cell))
    shape.finish(color=None, fill=BLACK)
    shape.commit()
    caption(
        page, (square.y1 + card.y1) / 2, f"{qr_id:02d}", side / 2 - 0.9 * cell,
        CARD * QR_CAPTION_HEIGHT, CARD * QR_CAPTION_ARROW, BLACK,
    )


def label_card(doc, notch_degrees):
    """A black card with a white field and a white notch cut through the frame."""
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    card = card_rect()
    frame = CARD * FRAME
    shape = page.new_shape()
    shape.draw_rect(card)
    shape.finish(color=None, fill=BLACK)
    # The notch starts at the top, then rotates.
    half = CARD * NOTCH / 2
    centre = pymupdf.Point(PAGE_W / 2, PAGE_H / 2)
    matrix = pymupdf.Matrix(notch_degrees)
    corners = [(-half, -CARD / 2), (half, -CARD / 2), (half, -CARD / 2 + frame + 1), (-half, -CARD / 2 + frame + 1)]
    shape.draw_polyline([pymupdf.Point(x, y) * matrix + centre for x, y in corners + corners[:1]])
    shape.finish(color=None, fill=WHITE)
    shape.draw_rect(card + (frame, frame, -frame, -frame))
    shape.finish(color=None, fill=WHITE)
    shape.commit()
    return page, card


def number_card(doc, number):
    page, card = label_card(doc, 0)
    label_digit(page, number)
    caption(
        page, card.y1 - CARD * FRAME / 2, f"{number:02d}", CARD * LABEL_CAPTION_ARROW_X,
        CARD * LABEL_CAPTION_HEIGHT, CARD * LABEL_CAPTION_ARROW, WHITE,
    )


def arrow_card(doc, name):
    # In the manual's picture, the notch sits at the arrow's tip.
    page, card = label_card(doc, ROTATIONS[name])
    draw_arrow(page, pymupdf.Point(PAGE_W / 2, PAGE_H / 2), CARD * ARROW_HEIGHT, ROTATIONS[name])


def cover(doc):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    x = 2.2 * CM
    page.insert_text((x, 3 * CM), "Hula print cards", fontsize=28, fontname="arialbd", fontfile=FONT_FILE)
    lines = [
        ("Contents", True),
        ("Pages 2-11: QR codes 0-9. Pages 12-21: number labels 0-9. Pages 22-25: arrow labels.", False),
        ("", False),
        ("Print settings", True),
        ("Print at 100% / Actual size, not Fit to page. Each card should measure 20 cm across.", False),
        ("Use matte paper or card, then glue it to stiff board so it stays flat.", False),
        ("QR cards: keep about 2.3 cm of white around the black square. Label cards: cut along the black edge.", False),
        ("", False),
        ("Test before printing a full set", True),
        ("These cards have not been tested on a drone.", False),
        ("QR codes follow the drone firmware's pattern, but their size is an estimate. Compare with your kit card.", False),
        ("The labels are based on small pictures in the manual. Try QR 1 and one label first.", False),
        ("Use Recognize QR code 1 or Recognize label, then check that the result equals 1.", False),
    ]
    y = 4.6 * CM
    for line, heading in lines:
        if line:
            page.insert_text((x, y), line, fontsize=15 if heading else 10.5, fontname="arialbd" if heading else "helv", fontfile=FONT_FILE if heading else None)
        y += 0.8 * CM


def main():
    doc = pymupdf.open()
    cover(doc)
    for qr_id in range(10):
        qr_card(doc, qr_id)
    for number in range(10):
        number_card(doc, number)
    for name in ROTATIONS:
        arrow_card(doc, name)
    doc.save(OUTPUT, garbage=4, deflate=True)
    print(f"{OUTPUT} ({doc.page_count} pages)")


if __name__ == "__main__":
    main()
