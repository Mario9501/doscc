/* ======================================================================
 * VIDEO.H - DOS video adapter library
 *
 * Auto-detects MDA, Hercules, CGA, EGA, VGA, PGA, and MCGA adapters.
 * Provides direct video memory output with automatic mono attribute
 * mapping for MDA/Hercules/EGA-mono/VGA-mono compatibility.
 *
 * MS C 5.0 / small model
 * ====================================================================== */

#ifndef VIDEO_H
#define VIDEO_H

/* ======================================================================
 * Adapter type constants
 * ====================================================================== */

#define VID_MDA         0
#define VID_HERCULES    1
#define VID_CGA         2
#define VID_EGA         3
#define VID_VGA         4
#define VID_PGA         5       /* IBM Professional Graphics Adapter */
#define VID_MCGA        6       /* IBM PS/2 Multi-Color Graphics Array */
#define VID_HERCPLUS    7       /* Hercules Graphics Card Plus */
#define VID_INCOLOR     8       /* Hercules InColor (16-color at B000) */
#define VID_COLORPLUS   9       /* Plantronics ColorPlus */

/* ======================================================================
 * Standard attributes
 * ====================================================================== */

#define VID_NORMAL      0x07    /* light grey on black */
#define VID_BOLD        0x0F    /* bright white on black */
#define VID_UNDERLINE   0x01    /* underline (mono only, appears as blue on color) */
#define VID_REVERSE     0x70    /* black on light grey */

/* ======================================================================
 * Screen dimensions
 * ====================================================================== */

#define VID_ROWS        25
#define VID_COLS        80

/* ======================================================================
 * CP 437 single-line box-drawing characters
 * ====================================================================== */

#define VID_BOX_TL      218     /* top-left corner */
#define VID_BOX_TR      191     /* top-right corner */
#define VID_BOX_BL      192     /* bottom-left corner */
#define VID_BOX_BR      217     /* bottom-right corner */
#define VID_BOX_H       196     /* horizontal line */
#define VID_BOX_V       179     /* vertical line */

/* ======================================================================
 * Detection
 * ====================================================================== */

/* Detect adapter and initialize library. Returns adapter type constant.
 * Must be called before any other vid_ function. */
int   vid_init(void);

/* Return current adapter type (VID_MDA .. VID_COLORPLUS). */
int   vid_type(void);

/* Return adapter name string ("MDA", "Hercules", "CGA", etc.). */
char *vid_type_name(void);

/* Return 1 if adapter is monochrome (MDA, Hercules, Hercules Plus,
 * EGA mono, VGA mono, or MCGA mono). Note: InColor returns 0 despite
 * using B000:0000 because it supports 16-color text attributes. */
int   vid_is_mono(void);

/* ======================================================================
 * Output (direct video memory)
 * ====================================================================== */

/* Write single character with attribute at (row, col). */
void  vid_putc(int row, int col, int ch, int attr);

/* Write null-terminated string with attribute starting at (row, col). */
void  vid_puts(int row, int col, char *s, int attr);

/* Write string padded/truncated to exactly n characters. */
void  vid_putsn(int row, int col, char *s, int n, int attr);

/* Fill count cells starting at (row, col) with ch and attribute. */
void  vid_fill(int row, int col, int ch, int attr, int count);

/* Clear entire screen with attribute. */
void  vid_clear(int attr);

/* Clear rows from start_row to end_row (inclusive) with attribute. */
void  vid_clear_rows(int start_row, int end_row, int attr);

/* ======================================================================
 * Scrolling (BIOS INT 10h)
 * ====================================================================== */

/* Scroll window up by n lines. Blank lines filled with attr. */
void  vid_scroll_up(int top, int bot, int left, int right, int n, int attr);

/* Scroll window down by n lines. Blank lines filled with attr. */
void  vid_scroll_down(int top, int bot, int left, int right, int n, int attr);

/* ======================================================================
 * Box drawing (CP 437 single-line)
 * ====================================================================== */

/* Draw a single-line box from (r1,c1) to (r2,c2). */
void  vid_box(int r1, int c1, int r2, int c2, int attr);

/* Draw horizontal line of n characters starting at (row, col). */
void  vid_hline(int row, int col, int n, int attr);

/* Draw vertical line of n characters starting at (row, col). */
void  vid_vline(int row, int col, int n, int attr);

/* ======================================================================
 * Hex output
 * ====================================================================== */

/* Write 2-digit hex byte at (row, col). */
void  vid_put_hex_byte(int row, int col, int val, int attr);

/* Write 4-digit hex word at (row, col). */
void  vid_put_hex_word(int row, int col, unsigned int val, int attr);

/* Write 8-digit hex long at (row, col). */
void  vid_put_hex_long(int row, int col, long val, int attr);

/* ======================================================================
 * Cursor (BIOS INT 10h)
 * ====================================================================== */

/* Set cursor position on page 0. */
void  vid_set_cursor_pos(int row, int col);

/* Get current cursor position on page 0. */
void  vid_get_cursor_pos(int *row, int *col);

/* Set cursor shape by start and end scan lines. */
void  vid_set_cursor_shape(int start, int end);

/* Hide cursor (moves shape off-screen). */
void  vid_hide_cursor(void);

/* Show cursor with default shape for detected adapter. */
void  vid_show_cursor(void);

/* ======================================================================
 * Attribute helper
 * ====================================================================== */

/* Map a color attribute to monochrome equivalent. No-op on color adapters. */
int   vid_map_attr(int attr);

#endif /* VIDEO_H */
