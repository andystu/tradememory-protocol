"""Generate blog cover image: Evolution Experiment"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# === Config ===
W, H = 1000, 420
DPI = 100
BG = '#0a0a0f'
BLUE = '#00b4ff'
BLUE_DIM = '#005f8a'
RED = '#ff4444'
GREEN = '#00dd88'
WHITE = '#ffffff'
GRAY = '#666666'
LIGHT_GRAY = '#aaaaaa'

fig, ax = plt.subplots(figsize=(W/DPI, H/DPI), dpi=DPI)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)
ax.set_xlim(0, 100)
ax.set_ylim(0, 42)
ax.axis('off')

# === Three phases layout ===
# Phase 1: Round 1 FAIL (left)
# Phase 2: Round 2 EVOLVED (center)
# Phase 3: Combined MERGED (right)

# --- Simulated equity curves ---
np.random.seed(42)

# Round 1: downward equity curve (Sharpe -1.20)
x1 = np.linspace(0, 1, 40)
y1_base = 100 - 0.21 * x1 * 100  # -0.21% total
noise1 = np.cumsum(np.random.normal(-0.015, 0.08, 40))
y1 = y1_base + noise1
y1 = (y1 - y1.min()) / (y1.max() - y1.min())  # normalize 0-1

# Round 2 Strategy C: upward equity curve (Sharpe 1.90)
x2 = np.linspace(0, 1, 40)
y2_base = np.linspace(0, 0.7, 40)
noise2 = np.cumsum(np.random.normal(0.008, 0.03, 40))
y2 = y2_base + noise2
y2 = (y2 - y2.min()) / (y2.max() - y2.min())

# Combined C+E: strong upward (Sharpe 3.84)
x3 = np.linspace(0, 1, 80)
y3_base = np.linspace(0, 1, 80)
noise3 = np.cumsum(np.random.normal(0.005, 0.015, 80))
y3 = y3_base + noise3
y3 = (y3 - y3.min()) / (y3.max() - y3.min())

# === Draw boxes ===
box_h = 18
box_y = 10
gap = 2

# Box 1: x=3..30
bx1, bw1 = 3, 27
# Box 2: x=36..63
bx2, bw2 = 36, 27
# Box 3: x=69..96
bx3, bw3 = 69, 27

for bx, bw, color in [(bx1, bw1, RED), (bx2, bw2, BLUE), (bx3, bw3, GREEN)]:
    border = patches.FancyBboxPatch(
        (bx, box_y), bw, box_h,
        boxstyle="round,pad=0.3",
        linewidth=1.5, edgecolor=color + '40', facecolor=BG,
        zorder=1
    )
    ax.add_patch(border)

# === Plot equity curves inside boxes ===
chart_pad_x = 1.5
chart_pad_y = 2
chart_h = 10
chart_y_base = box_y + 2

def plot_curve(bx, bw, x_data, y_data, color, label_sharpe, label_status, status_color):
    cx_start = bx + chart_pad_x
    cx_end = bx + bw - chart_pad_x
    cy_start = chart_y_base
    cy_end = chart_y_base + chart_h

    px = cx_start + x_data * (cx_end - cx_start)
    py = cy_start + y_data * (cy_end - cy_start)

    # Gradient fill under curve
    ax.fill_between(px, cy_start, py, color=color, alpha=0.08, zorder=2)
    ax.plot(px, py, color=color, linewidth=2, alpha=0.9, zorder=3)

    # Sharpe label inside box top
    ax.text(bx + bw/2, box_y + box_h - 1.5, f'Sharpe {label_sharpe}',
            color=color, fontsize=13, fontweight='bold',
            ha='center', va='center', zorder=4,
            fontfamily='monospace')

# Plot all three
plot_curve(bx1, bw1, x1, y1, RED, '-1.20', 'FAIL', RED)
plot_curve(bx2, bw2, x2, y2, BLUE, '1.90', 'EVOLVED', BLUE)
plot_curve(bx3, bw3, x3, y3, GREEN, '3.84', 'MERGED', GREEN)

# === Status labels below boxes ===
label_y = box_y - 1.5
ax.text(bx1 + bw1/2, label_y, 'Round 1: FAIL', color=RED, fontsize=10,
        ha='center', va='center', fontweight='bold', fontfamily='monospace')
ax.text(bx2 + bw2/2, label_y, 'Round 2: EVOLVED', color=BLUE, fontsize=10,
        ha='center', va='center', fontweight='bold', fontfamily='monospace')
ax.text(bx3 + bw3/2, label_y, 'Combined: 3.84', color=GREEN, fontsize=10,
        ha='center', va='center', fontweight='bold', fontfamily='monospace')

# === Arrows between boxes ===
arrow_y = box_y + box_h / 2
for ax1_end, ax2_start in [(bx1 + bw1 + 0.3, bx2 - 0.3), (bx2 + bw2 + 0.3, bx3 - 0.3)]:
    ax.annotate('', xy=(ax2_start, arrow_y), xytext=(ax1_end, arrow_y),
                arrowprops=dict(arrowstyle='->', color=BLUE_DIM, lw=2.5,
                               connectionstyle='arc3,rad=0'),
                zorder=5)

# === Title ===
ax.text(50, 38, 'I Let AI Invent Its Own Trading Strategies',
        color=WHITE, fontsize=16, fontweight='bold',
        ha='center', va='center', zorder=10,
        fontfamily='sans-serif')

# === Subtitle ===
ax.text(50, 34.5, 'Zero indicators. Zero human rules. Pure evolution.',
        color=LIGHT_GRAY, fontsize=10, ha='center', va='center', zorder=10,
        fontfamily='sans-serif', style='italic')

# === Bottom stats bar ===
stats_y = 5.5
stats = [
    ('477 trades', GRAY),
    ('91% months profitable', GRAY),
    ('0.22% max drawdown', GRAY),
    ('$0.016/evolution', GRAY),
]
total_w = 90
spacing = total_w / (len(stats))
for i, (text, color) in enumerate(stats):
    sx = 5 + spacing * i + spacing/2
    ax.text(sx, stats_y, text, color=LIGHT_GRAY, fontsize=8,
            ha='center', va='center', fontfamily='monospace', alpha=0.7)

# Separator dots between stats
for i in range(len(stats) - 1):
    sx = 5 + spacing * (i + 1)
    ax.text(sx, stats_y, '·', color=GRAY, fontsize=10,
            ha='center', va='center', alpha=0.5)

# === Brand ===
ax.text(97, 2, 'mnemox.ai', color=BLUE, fontsize=7, ha='right', va='center',
        fontfamily='monospace', alpha=0.6)

# === Save ===
plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
out_path = r'C:\Users\johns\projects\tradememory-protocol\docs\blog-cover.png'
fig.savefig(out_path, dpi=DPI, facecolor=BG, edgecolor='none',
            bbox_inches='tight', pad_inches=0.1)
plt.close()
print(f'Saved: {out_path}')
