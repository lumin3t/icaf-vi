from PIL import Image, ImageDraw, ImageFont
import os, datetime, textwrap

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
FONT_SIZE = 15
PAD       = 18
LINE_H    = 21
WIN_W     = 900
TITLE_H   = 32

# Colours
BG        = (48,  10,  36)
TITLE_BG  = (60,  20,  48)
TITLE_FG  = (210, 190, 210)
DOT_R     = (255,  95,  87)
DOT_Y     = (255, 189,  46)
DOT_G     = ( 39, 201,  63)
C_PROMPT  = ( 90, 180,  90)   # green prompt
C_CMD     = (220, 220, 220)   # white command text
C_OUT     = (200, 200, 200)   # normal output
C_REJECT  = (255, 100, 100)   # red — bad password / unchanged
C_ACCEPT  = (100, 230, 130)   # green — password changed
C_DIM     = (150, 120, 140)   # dimmed
C_PASS_BG = ( 20,  60,  20)
C_FAIL_BG = ( 70,  20,  20)


def _fonts():
    try:
        return ImageFont.truetype(FONT_PATH, FONT_SIZE), ImageFont.truetype(FONT_BOLD, FONT_SIZE)
    except Exception:
        f = ImageFont.load_default()
        return f, f


def _title_bar(draw, width, title, fb):
    draw.rectangle([0, 0, width, TITLE_H], fill=TITLE_BG)
    for i, col in enumerate([DOT_R, DOT_Y, DOT_G]):
        cx = 14 + i * 20
        draw.ellipse([cx-5, TITLE_H//2-5, cx+5, TITLE_H//2+5], fill=col)
    bbox = fb.getbbox(title)
    tw   = bbox[2] - bbox[0]
    draw.text(((width - tw) // 2, 7), title, font=fb, fill=TITLE_FG)


def _line_colour(text):
    low = text.lower()
    if any(k in low for k in ["bad password", "too short", "too weak", "unchanged",
                               "incorrect password", "not acceptable", "error"]):
        return C_REJECT
    if any(k in low for k in ["password changed", "changed by root", "success", "connected"]):
        return C_ACCEPT
    return C_OUT


def render_ubuntu_terminal_screenshot(tc_id, tc_name, command, output, verdict, output_dir):
    """
    Renders a realistic Ubuntu terminal Pillow screenshot.
    Shows: SSH login → command → raw output → verdict bar.
    Keeps it minimal — just the command and what the DUT returned.
    """
    font, fb = _fonts()
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── Build line list ───────────────────────────────────────────────────
    # Each entry: (kind, text)
    #   kind = "prompt_ubuntu" | "prompt_root" | "out" | "verdict"
    ubuntu_prompt = "bhavya@Ubuntu:~/password_policy_test$ "
    root_prompt   = "root@localhost:~# "

    rows = []
    rows.append(("prompt_ubuntu", ubuntu_prompt, "ssh root@192.168.56.102"))
    rows.append(("out",           "",             "root@192.168.56.102's password:"))
    rows.append(("out",           "",             "Welcome to Alpine Linux"))
    rows.append(("out",           "",             ""))

    # Main command
    rows.append(("prompt_root", root_prompt, command))

    # Output lines — raw, no prefix
    for line in (output or "").strip().splitlines():
        rows.append(("out", "", line))

    rows.append(("out", "", ""))
    rows.append(("verdict", "", f"  [{ts}]  {tc_id}  VERDICT: {verdict}"))

    # ── Size image to fit ─────────────────────────────────────────────────
    img_h = TITLE_H + len(rows) * LINE_H + PAD * 2
    img   = Image.new("RGB", (WIN_W, img_h), BG)
    draw  = ImageDraw.Draw(img)

    _title_bar(draw, WIN_W,
               f"bhavya@Ubuntu: ~/password_policy_test  |  {ts}", fb)

    y = TITLE_H + PAD
    for kind, prefix, text in rows:
        text = text.replace('changed by root', 'changed')  # clean output
        if kind == "verdict":
            draw.rectangle([0, y-2, WIN_W, y + LINE_H],
                           fill=C_PASS_BG if verdict == "PASS" else C_FAIL_BG)
            col = C_ACCEPT if verdict == "PASS" else C_REJECT
            draw.text((PAD, y), text, font=fb, fill=col)

        elif kind in ("prompt_ubuntu", "prompt_root"):
            draw.text((PAD, y), prefix, font=font, fill=C_PROMPT)
            x_cmd = PAD + int(font.getlength(prefix))
            draw.text((x_cmd, y), text, font=fb, fill=C_CMD)

        else:
            col = _line_colour(text)
            draw.text((PAD, y), text, font=font, fill=col)

        y += LINE_H

    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{tc_id}_terminal.png")
    img.save(path)
    return path
