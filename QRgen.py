import qrcode
import math
import random

from collections import defaultdict

FINDER_PATTERN_SIZE = 12

def qr_to_matrix(data: str):
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H
    )
    qr.add_data(data)
    qr.make(fit=True)

    matrix = qr.get_matrix()
    return matrix

def remove_finder_patterns(matrix):
    n = len(matrix)

    # top left
    for i in range(FINDER_PATTERN_SIZE):
        for j in range(FINDER_PATTERN_SIZE):
            matrix[i][j] = 0

    # top right
    for i in range(FINDER_PATTERN_SIZE):
        for j in range(n-FINDER_PATTERN_SIZE, n):
            matrix[i][j] = 0

    # bottom left
    for i in range(n-FINDER_PATTERN_SIZE, n):
        for j in range(FINDER_PATTERN_SIZE):
            matrix[i][j] = 0

    return matrix


#TODO: add inverse middle one - white with 4 sides covered
def group_matrix(matrix):
    size = len(matrix) - 1
    groups = []

    for y in range(size):
        for x in range(size):
            if matrix[y][x]:
                square_flags = {
                    "top_left": False,
                    "top": False,
                    "top_right": False,
                    "left": False,
                    "mid_only": False, #true only if its only rest is false
                    "right": False,
                    "bot_left": False,
                    "bot": False,
                    "bot_right": False,
                    "point": False
                    }
                right_check = False
                left_check = False
                bot_check = False
                top_check = False

                if x > 0:
                    right_check = True
                if x < size:
                    left_check = True
                if y > 0:
                    bot_check = True
                if y < size:
                    top_check = True

                #QR code is rotated 90 degrees, that's why right is left, top is bot
                # names for variables are names for directions of final QR code 
                # checks are not reliable names
                if bot_check:
                    if not matrix[y-1][x]:
                        square_flags["left"] = True
                if bot_check and right_check:
                    # if not matrix[y-1][x-1] and not matrix[y-1][x] and not matrix [y][x-1]:
                    if not matrix[y-1][x] and not matrix [y][x-1]:
                        square_flags["top_left"] = True
                if bot_check and left_check:
                    # if not matrix[y-1][x+1] and not matrix[y][x+1] and not matrix[y-1][x]:
                    if  not matrix[y][x+1] and not matrix[y-1][x]:
                        square_flags["bot_left"] = True

                if right_check:
                    if not matrix[y][x-1]:
                        square_flags["top"] = True
                if left_check:
                    if not matrix[y][x+1]:
                        square_flags["bot"] = True

                if top_check:
                    if not matrix[y+1][x]:
                        square_flags["right"] = True
                if top_check and left_check:
                    # if not matrix[y+1][x+1] and not matrix[y+1][x] and not matrix[y][x+1]:
                    if not matrix[y+1][x] and not matrix[y][x+1]:
                        square_flags["bot_right"] = True
                if top_check and right_check:
                    # if not matrix[y+1][x-1] and not matrix[y+1][x] and not matrix[y][x-1]:
                    if not matrix[y+1][x] and not matrix[y][x-1]:
                        square_flags["top_right"] = True

                if not any(v for k, v in square_flags.items() if k != "mid_only"):
                    square_flags["mid_only"] = True

                if all(v for k, v in square_flags.items() if k != "mid_only" and k != "point"):
                    square_flags["point"] = True
                    square_flags["top_left"] = False,
                    square_flags["top"] = False
                    square_flags["top_right"] = False
                    square_flags["left"] = False
                    square_flags["mid_only"] = False
                    square_flags["right"] = False
                    square_flags["bot_left"] = False
                    square_flags["bot"] =  False
                    square_flags["bot_right"] = False


                group = {
                    "pos": (x,y),
                    "flags": square_flags
                }
                
                groups.append(group)
                
    return groups

def _path_round_rect_selective(x, y, w, h, r_tl, r_tr, r_br, r_bl):
    """
    returns d=... for <path> of corner 
    r in px.
    """
    rmax = min(w, h) / 2.0
    r_tl = max(0.0, min(float(r_tl), rmax))
    r_tr = max(0.0, min(float(r_tr), rmax))
    r_br = max(0.0, min(float(r_br), rmax))
    r_bl = max(0.0, min(float(r_bl), rmax))

    # start w lewym górnym, po krawędziach zgodnie z ruchem wskazówek
    d = []
    d.append(f"M {x + r_tl:.3f},{y:.3f}")

    # top edge -> TR
    d.append(f"H {x + w - r_tr:.3f}")
    if r_tr:
        d.append(f"A {r_tr:.3f},{r_tr:.3f} 0 0 1 {x + w:.3f},{y + r_tr:.3f}")
    else:
        d.append(f"L {x + w:.3f},{y:.3f}")

    # right edge -> BR
    d.append(f"V {y + h - r_br:.3f}")
    if r_br:
        d.append(f"A {r_br:.3f},{r_br:.3f} 0 0 1 {x + w - r_br:.3f},{y + h:.3f}")
    else:
        d.append(f"L {x + w:.3f},{y + h:.3f}")

    # bottom edge -> BL
    d.append(f"H {x + r_bl:.3f}")
    if r_bl:
        d.append(f"A {r_bl:.3f},{r_bl:.3f} 0 0 1 {x:.3f},{y + h - r_bl:.3f}")
    else:
        d.append(f"L {x:.3f},{y + h:.3f}")

    # left edge -> TL
    d.append(f"V {y + r_tl:.3f}")
    if r_tl:
        d.append(f"A {r_tl:.3f},{r_tl:.3f} 0 0 1 {x + r_tl:.3f},{y:.3f}")
    else:
        d.append(f"L {x:.3f},{y:.3f}")

    d.append("Z")
    return " ".join(d)


def module_shape_from_flags(flags, sx, sy, module_size):
    """
    Zwraca listę stringów SVG elementów dla pojedynczego modułu.
    flags: dict jak u Ciebie.
    sx, sy: top-left modułu w px.
    """
    ms = module_size
    cx = sx + ms / 2.0
    cy = sy + ms / 2.0


    r = ms * 0.8  # r for rounding corners

    out = []

    if flags.get("point"):
        rr = ms * 0.4
        out.append(f'<rect width="{ms}" height="{ms}" x="{sx}" y="{sy}" rx="{rr:.3f}" ry="{rr:.3f}" />')
        # p1x, p1y = int(sx + ms * 0.8) , int(sy + ms * 0.8)
        # p2x, p2y = int(sx + ms * 0.5) , sy
        # p3x, p3y = int(sx + ms * 0.2) , int(sy + ms * 0.8)
        # p4x, p4y = int(sx + ms * 0.95) , int(sy + ms * 0.35)
        # p5x, p5y = int(sx + ms * 0.05) , int(sy + ms * 0.35)
        # out.append(f'<polygon points="{p1x},{p1y} {p2x},{p2y} {p3x},{p3y} {p4x},{p4y} {p5x},{p5y}" />')
        return out

    r_tl = r if flags.get("top_left") else 0.0
    r_tr = r if flags.get("top_right") else 0.0
    r_br = r if flags.get("bot_right") else 0.0
    r_bl = r if flags.get("bot_left") else 0.0


    # 4) Jeśli nie ma żadnego rounding -> zwykły rect (szybciej i czyściej)
    if (r_tl == 0 and r_tr == 0 and r_br == 0 and r_bl == 0):
        out.append(f'<rect x="{sx}" y="{sy}" width="{ms}" height="{ms}" />')
        return out

    # 5) W przeciwnym wypadku -> path z selektywnym roundingiem
    d = _path_round_rect_selective(sx, sy, ms, ms, r_tl, r_tr, r_br, r_bl)
    out.append(f'<path d="{d}" />')
    return out

def vertical_group_filter(groups):
    for g in groups:
        if g["flags"]["top"] and (g["flags"]["top_left"] or g["flags"]["top_right"]):
            g["flags"]["top"] = False
        if g["flags"]["bot"] and (g["flags"]["bot_left"] or g["flags"]["bot_right"]):
            g["flags"]["bot"] = False
    return groups

def horizontal_group_filter(groups):
    for g in groups:
        if g["flags"]["right"] and (g["flags"]["bot_right"] or g["flags"]["top_right"]):
            g["flags"]["right"] = False
        if g["flags"]["left"] and (g["flags"]["bot_left"] or g["flags"]["top_left"]):
            g["flags"]["left"] = False
    return groups 

#TODO custom finder squares
def add_find_squares():
    return 1

def draw_squares(groups, module_size=16):
    svg = []
    svg.append('<svg xmlns="http://www.w3.org/2000/svg" '
               'stroke="none" fill="black">')

    for g in groups:
        y, x = g["pos"]

        sx = x * module_size
        sy = y * module_size

        elems = module_shape_from_flags(g["flags"], sx, sy, module_size)
        svg.extend(elems)
       
        

    svg.append('</svg>')
    return "\n".join(svg)


m = qr_to_matrix("https://example.com")
#m = remove_finder_patterns(m)
groups = group_matrix(m)
groups = horizontal_group_filter(groups=groups)
groups = vertical_group_filter(groups=groups)


paths = []


svg = draw_squares(groups=groups, module_size=16)

with open("generated_qr.svg", "w", encoding="utf-8") as f:
    f.write(svg)


