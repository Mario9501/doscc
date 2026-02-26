/* ======================================================================
 * VIDEO.C - DOS video adapter library implementation
 *
 * Auto-detects video adapters via cascading probe:
 *   1. INT 10h AH=1Ah  (VGA/PS2 BIOS display codes)
 *   2. INT 10h AH=12h  (EGA BIOS alternate select)
 *   3. PGA comm buffer  (read-only probe at C600:0300)
 *   4. INT 11h          (equipment word - mono vs color)
 *   5. Port 3BAh        (Hercules retrace toggle + card ID)
 *   6. Port 3DDh        (Plantronics ColorPlus register)
 *
 * Detected adapters:
 *   MDA, Hercules, Hercules Plus, InColor, CGA, ColorPlus,
 *   EGA, VGA, PGA, MCGA
 *
 * All output goes through direct video memory writes with automatic
 * mono attribute mapping on monochrome adapters. The InColor is a
 * special case: it sits at B000:0000 but supports 16-color text,
 * so mono remapping is NOT applied.
 *
 * MS C 5.0 / small model
 * ====================================================================== */

#include <dos.h>
#include <conio.h>
#include "video.h"

/* ======================================================================
 * Internal state
 * ====================================================================== */

static char far *vid_base;          /* B000:0000 (mono) or B800:0000 (color) */
static int vid_adapter_type;        /* VID_MDA .. VID_COLORPLUS */
static int vid_mono;                /* 1 if mono attribute mapping needed */

static char *type_names[] = {
    "MDA", "Hercules", "CGA", "EGA", "VGA", "PGA", "MCGA",
    "Hercules Plus", "InColor", "ColorPlus"
};
static char hex_digits[] = "0123456789ABCDEF";

/* ======================================================================
 * Adapter detection
 * ====================================================================== */

static void vid_set(int type, int mono)
{
    vid_adapter_type = type;
    vid_mono = mono;
    vid_base = mono ? (char far *)0xB0000000L : (char far *)0xB8000000L;
}

/* Like vid_set but with explicit base address. Used for cards like
 * InColor that sit at B000:0000 but support full color attributes. */
static void vid_set_ex(int type, int mono, char far *base)
{
    vid_adapter_type = type;
    vid_mono = mono;
    vid_base = base;
}

/* --- PGA detection (read-only probe) ---
 * The IBM Professional Graphics Adapter has a communications buffer
 * at C600:0000 with a status/command area. On an empty bus the read
 * returns 0xFF; the PGA's idle status byte is different. We also
 * sample a second byte to reduce false positives from ROMs that
 * happen to have non-FF data at that address. */
static int detect_pga(void)
{
    char far *pga_stat = (char far *)0xC6000300L;
    char far *pga_cmd  = (char far *)0xC6000000L;
    unsigned char s, c;

    s = *pga_stat;
    if (s == 0xFF)
        return 0;           /* bus float - no hardware here */

    /* The PGA status byte when idle is 0x00; its command byte should
     * also not be 0xFF. Check both to avoid ROM false positives. */
    c = *pga_cmd;
    if (c == 0xFF)
        return 0;

    /* Additional sanity: status should be 0x00-0x0F when idle.
     * Values above that are unlikely from a real PGA. */
    if (s > 0x0F)
        return 0;

    return 1;
}

int vid_init(void)
{
    union REGS regs;
    int equip, i, val, changed;

    /* --- Step 1: VGA/PS2 identification (INT 10h AH=1Ah) ---
     * Supported by VGA, MCGA, and some late EGA BIOSes.
     * AL returns 1Ah on success; BL gives the active display code:
     *   01h=MDA  02h=CGA  04h=EGA color  05h=EGA mono
     *   06h=PGA  07h=VGA mono  08h=VGA color
     *   0Ah=MCGA digital color  0Bh=MCGA analog mono  0Ch=MCGA analog color */
    regs.h.ah = 0x1A;
    regs.h.al = 0x00;
    int86(0x10, &regs, &regs);

    if (regs.h.al == 0x1A) {
        switch (regs.h.bl) {
        case 0x01:
            vid_set(VID_MDA, 1);
            return VID_MDA;
        case 0x02:
            vid_set(VID_CGA, 0);
            return VID_CGA;
        case 0x04:
            vid_set(VID_EGA, 0);
            return VID_EGA;
        case 0x05:
            vid_set(VID_EGA, 1);
            return VID_EGA;
        case 0x06:
            /* IBM Professional Graphics Adapter - uses B800:0000 for
             * text mode. Color adapter with its own graphics processor. */
            vid_set(VID_PGA, 0);
            return VID_PGA;
        case 0x07:
            vid_set(VID_VGA, 1);
            return VID_VGA;
        case 0x08:
            vid_set(VID_VGA, 0);
            return VID_VGA;
        case 0x0A:
            /* MCGA with digital color monitor (CGA-compatible) */
            vid_set(VID_MCGA, 0);
            return VID_MCGA;
        case 0x0B:
            /* MCGA with analog monochrome monitor */
            vid_set(VID_MCGA, 1);
            return VID_MCGA;
        case 0x0C:
            /* MCGA with analog color monitor */
            vid_set(VID_MCGA, 0);
            return VID_MCGA;
        }
    }

    /* --- Step 2: EGA detection (INT 10h AH=12h BL=10h) ---
     * If BL changes from 10h, EGA is present. BH=0 color, BH=1 mono. */
    regs.h.ah = 0x12;
    regs.h.bl = 0x10;
    int86(0x10, &regs, &regs);

    if (regs.h.bl != 0x10) {
        vid_set(VID_EGA, regs.h.bh != 0);
        return VID_EGA;
    }

    /* --- Step 3: PGA detection (communications buffer probe) ---
     * The PGA predates VGA so INT 10h AH=1Ah may not be available on
     * the original IBM PGA BIOS. Probe its comm buffer at C600:0300
     * before falling through to CGA/MDA detection. */
    if (detect_pga()) {
        vid_set(VID_PGA, 0);
        return VID_PGA;
    }

    /* --- Step 4: Equipment word (INT 11h) ---
     * Bits 4-5: 11b = monochrome adapter (MDA or Hercules) */
    int86(0x11, &regs, &regs);
    equip = regs.x.ax;

    if (((equip >> 4) & 0x03) == 0x03) {
        /* Monochrome adapter - distinguish MDA from Hercules */
        vid_base = (char far *)0xB0000000L;

        /* --- Step 5: Hercules detection (port 3BAh bit 7) ---
         * Read status port in a loop. On Hercules the vertical retrace
         * bit (bit 7) toggles; on MDA it stays constant. */
        val = inp(0x3BA) & 0x80;
        changed = 0;
        for (i = 0; i < 32768; i++) {
            if ((inp(0x3BA) & 0x80) != val) {
                changed = 1;
                break;
            }
        }

        if (changed) {
            /* Hercules family detected. Read card ID from bits 6-4
             * of the status register to distinguish variants:
             *   000 = Hercules Graphics Card (HGC)
             *   001 = Hercules Graphics Card Plus (HGC+)
             *   101 = Hercules InColor Card */
            switch ((inp(0x3BA) >> 4) & 0x07) {
            case 1:
                /* HGC+ supports RAM-loadable fonts (up to 4096 glyphs)
                 * but text attributes are still monochrome. */
                vid_set(VID_HERCPLUS, 1);
                return VID_HERCPLUS;
            case 5:
                /* InColor uses B000:0000 but has full 16-color text
                 * via EGA-like planar attribute handling. Do NOT apply
                 * mono attribute mapping - treat as color adapter. */
                vid_set_ex(VID_INCOLOR, 0, (char far *)0xB0000000L);
                return VID_INCOLOR;
            default:
                vid_set(VID_HERCULES, 1);
                return VID_HERCULES;
            }
        }
        vid_set(VID_MDA, 1);
        return VID_MDA;
    }

    /* --- Step 6: CGA default ---
     * Also covers clones and the IBM Enhanced Color Adapter when no
     * EGA BIOS is present. Before accepting plain CGA, probe for
     * enhanced CGA variants that 86Box and real hardware support. */

    /* --- Plantronics ColorPlus detection (port 3DDh) ---
     * The ColorPlus has an extended mode register at 3DDh that
     * controls plane separation for 16-color graphics. On standard
     * CGA this port is undecoded and reads back bus float (0xFF).
     * Write two different values and check that both read back. */
    outp(0x3DD, 0x55);
    if (inp(0x3DD) == 0x55) {
        outp(0x3DD, 0xAA);
        if (inp(0x3DD) == 0xAA) {
            outp(0x3DD, 0x00);      /* restore normal mode */
            vid_set(VID_COLORPLUS, 0);
            return VID_COLORPLUS;
        }
    }
    outp(0x3DD, 0x00);

    vid_set(VID_CGA, 0);
    return VID_CGA;
}

/* ======================================================================
 * Adapter info
 * ====================================================================== */

int vid_type(void)
{
    return vid_adapter_type;
}

char *vid_type_name(void)
{
    return type_names[vid_adapter_type];
}

int vid_is_mono(void)
{
    return vid_mono;
}

/* ======================================================================
 * Attribute mapping
 *
 * On MDA/Hercules, color attributes are mapped to the limited set of
 * monochrome attributes the hardware supports:
 *   bg != 0        -> reverse video (0x70)
 *   fg intensity    -> bold (0x0F)
 *   fg == 1        -> underline (0x01)
 *   fg == bg == 0  -> invisible (0x00)
 *   otherwise      -> normal (0x07)
 *   blink bit 7    -> preserved
 * ====================================================================== */

int vid_map_attr(int attr)
{
    int fg, bg, blink, mapped;

    if (!vid_mono)
        return attr;

    blink = attr & 0x80;
    fg = attr & 0x0F;
    bg = (attr >> 4) & 0x07;

    if (fg == 0 && bg == 0)
        mapped = 0x00;
    else if (bg != 0)
        mapped = 0x70;
    else if (fg & 0x08)
        mapped = 0x0F;
    else if (fg == 1)
        mapped = 0x01;
    else
        mapped = 0x07;

    return mapped | blink;
}

/* ======================================================================
 * Output primitives (direct video memory)
 * ====================================================================== */

void vid_putc(int row, int col, int ch, int attr)
{
    char far *p;
    int a;

    a = vid_mono ? vid_map_attr(attr) : attr;
    p = vid_base + ((row * VID_COLS + col) << 1);
    *p = (char)ch;
    *(p + 1) = (char)a;
}

void vid_puts(int row, int col, char *s, int attr)
{
    char far *p;
    int a;

    a = vid_mono ? vid_map_attr(attr) : attr;
    p = vid_base + ((row * VID_COLS + col) << 1);

    while (*s) {
        *p = *s++;
        *(p + 1) = (char)a;
        p += 2;
    }
}

void vid_putsn(int row, int col, char *s, int n, int attr)
{
    char far *p;
    int a, i;

    a = vid_mono ? vid_map_attr(attr) : attr;
    p = vid_base + ((row * VID_COLS + col) << 1);

    for (i = 0; i < n; i++) {
        *p = *s ? *s++ : ' ';
        *(p + 1) = (char)a;
        p += 2;
    }
}

void vid_fill(int row, int col, int ch, int attr, int count)
{
    char far *p;
    int a, i;

    a = vid_mono ? vid_map_attr(attr) : attr;
    p = vid_base + ((row * VID_COLS + col) << 1);

    for (i = 0; i < count; i++) {
        *p = (char)ch;
        *(p + 1) = (char)a;
        p += 2;
    }
}

void vid_clear(int attr)
{
    vid_fill(0, 0, ' ', attr, VID_ROWS * VID_COLS);
}

void vid_clear_rows(int start_row, int end_row, int attr)
{
    vid_fill(start_row, 0, ' ', attr, (end_row - start_row + 1) * VID_COLS);
}

/* ======================================================================
 * Scrolling (BIOS INT 10h AH=06h/07h)
 * ====================================================================== */

void vid_scroll_up(int top, int bot, int left, int right, int n, int attr)
{
    union REGS regs;

    regs.h.ah = 0x06;
    regs.h.al = (unsigned char)n;
    regs.h.bh = (unsigned char)(vid_mono ? vid_map_attr(attr) : attr);
    regs.h.ch = (unsigned char)top;
    regs.h.cl = (unsigned char)left;
    regs.h.dh = (unsigned char)bot;
    regs.h.dl = (unsigned char)right;
    int86(0x10, &regs, &regs);
}

void vid_scroll_down(int top, int bot, int left, int right, int n, int attr)
{
    union REGS regs;

    regs.h.ah = 0x07;
    regs.h.al = (unsigned char)n;
    regs.h.bh = (unsigned char)(vid_mono ? vid_map_attr(attr) : attr);
    regs.h.ch = (unsigned char)top;
    regs.h.cl = (unsigned char)left;
    regs.h.dh = (unsigned char)bot;
    regs.h.dl = (unsigned char)right;
    int86(0x10, &regs, &regs);
}

/* ======================================================================
 * Box drawing (CP 437 single-line characters)
 * ====================================================================== */

void vid_hline(int row, int col, int n, int attr)
{
    vid_fill(row, col, VID_BOX_H, attr, n);
}

void vid_vline(int row, int col, int n, int attr)
{
    int i;

    for (i = 0; i < n; i++)
        vid_putc(row + i, col, VID_BOX_V, attr);
}

void vid_box(int r1, int c1, int r2, int c2, int attr)
{
    /* Corners */
    vid_putc(r1, c1, VID_BOX_TL, attr);
    vid_putc(r1, c2, VID_BOX_TR, attr);
    vid_putc(r2, c1, VID_BOX_BL, attr);
    vid_putc(r2, c2, VID_BOX_BR, attr);

    /* Horizontal edges */
    vid_hline(r1, c1 + 1, c2 - c1 - 1, attr);
    vid_hline(r2, c1 + 1, c2 - c1 - 1, attr);

    /* Vertical edges */
    vid_vline(r1 + 1, c1, r2 - r1 - 1, attr);
    vid_vline(r1 + 1, c2, r2 - r1 - 1, attr);
}

/* ======================================================================
 * Hex output
 * ====================================================================== */

void vid_put_hex_byte(int row, int col, int val, int attr)
{
    vid_putc(row, col,     hex_digits[(val >> 4) & 0x0F], attr);
    vid_putc(row, col + 1, hex_digits[val & 0x0F], attr);
}

void vid_put_hex_word(int row, int col, unsigned int val, int attr)
{
    vid_put_hex_byte(row, col,     (val >> 8) & 0xFF, attr);
    vid_put_hex_byte(row, col + 2, val & 0xFF, attr);
}

void vid_put_hex_long(int row, int col, long val, int attr)
{
    vid_put_hex_word(row, col,     (unsigned int)((val >> 16) & 0xFFFFL), attr);
    vid_put_hex_word(row, col + 4, (unsigned int)(val & 0xFFFFL), attr);
}

/* ======================================================================
 * Cursor control (BIOS INT 10h)
 * ====================================================================== */

void vid_set_cursor_pos(int row, int col)
{
    union REGS regs;

    regs.h.ah = 0x02;
    regs.h.bh = 0x00;
    regs.h.dh = (unsigned char)row;
    regs.h.dl = (unsigned char)col;
    int86(0x10, &regs, &regs);
}

void vid_get_cursor_pos(int *row, int *col)
{
    union REGS regs;

    regs.h.ah = 0x03;
    regs.h.bh = 0x00;
    int86(0x10, &regs, &regs);
    *row = regs.h.dh;
    *col = regs.h.dl;
}

void vid_set_cursor_shape(int start, int end)
{
    union REGS regs;

    regs.h.ah = 0x01;
    regs.h.ch = (unsigned char)start;
    regs.h.cl = (unsigned char)end;
    int86(0x10, &regs, &regs);
}

void vid_hide_cursor(void)
{
    vid_set_cursor_shape(0x20, 0x00);
}

void vid_show_cursor(void)
{
    /* Default cursor shape per adapter type (scan line pairs):
     * MDA/HGC/HGC+/InColor: 11-12 (14-line character cell)
     * CGA/PGA/ColorPlus:     6-7  (8-line character cell)
     * EGA/VGA:               11-12 (varies, but standard default)
     * MCGA:                  13-14 (16-line character cell) */
    switch (vid_adapter_type) {
    case VID_CGA:
    case VID_PGA:
    case VID_COLORPLUS:
        vid_set_cursor_shape(6, 7);
        break;
    case VID_MCGA:
        if (vid_mono)
            vid_set_cursor_shape(11, 12);
        else
            vid_set_cursor_shape(13, 14);
        break;
    default:
        /* MDA, Hercules, HGC+, InColor, EGA, VGA */
        vid_set_cursor_shape(11, 12);
        break;
    }
}
