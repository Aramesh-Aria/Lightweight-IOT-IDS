"""Shared matplotlib style for all project figures (phases 2 and 3).

Colors come from design-reference.md. The reference navy (#111a2b) and teal
(#0b6e66) are too dark / too gray for chart marks (they fail the dataviz
validator's lightness band and chroma floor on the paper surface), so the
chart marks use lifted steps of the same hues. The original navy stays as the
text ink. Validated with dataviz/scripts/validate_palette.js on #fbf9f4:
FI, PFI and ALERT pass all six checks (all pairs). MI gets a contrast WARN,
so MI lines must be direct-labeled.

Labels in figures are English and set in Instrument Sans (fonts/latin).
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

FONT_DIR = Path(__file__).resolve().parents[2] / "fonts" / "latin"
FONT_FAMILY = "Instrument Sans"
DPI = 200

# Surfaces and ink
PAPER = "#fbf9f4"
INK = "#111a2b"
INK_2 = "#3a4356"
MUTED = "#7b8191"
GRID = "#e6e9ee"
RULE = "#d8d2c4"
SOFT_ORANGE = "#f7eadb"
SOFT_GREEN = "#e2efec"

# Method colors (fixed: color follows the method, never its rank)
METHOD_COLORS = {
    "FI": "#3157a8",    # navy family
    "PFI": "#00897b",   # teal family
    "MI": "#c4842f",    # light orange family (phase 3, direct-label it)
    "PCA": "#7b8191",   # neutral gray
}
ALERT = "#b4530b"       # leakage, MITM, differences from the paper
NEUTRAL = INK_2         # clean / reference series when not a method

# Sequential ramp (one hue, light -> dark) for confusion matrices
SEQ_CMAP = LinearSegmentedColormap.from_list("ink_seq", [PAPER, "#c9d3e6", "#3157a8", INK])

_applied = False


def apply() -> None:
    """Register the fonts and set rcParams once."""
    global _applied
    if _applied:
        return
    for f in FONT_DIR.glob("InstrumentSans-*.ttf"):
        font_manager.fontManager.addfont(str(f))
    plt.rcParams.update(
        {
            "font.family": [FONT_FAMILY, "DejaVu Sans"],  # fallback for ± only
            "font.size": 9.5,
            "axes.titlesize": 11,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
            "axes.titlecolor": INK,
            "axes.labelsize": 9.5,
            "axes.labelcolor": INK_2,
            "axes.edgecolor": RULE,
            "axes.linewidth": 0.8,
            "axes.facecolor": PAPER,
            "axes.grid": True,
            "axes.axisbelow": True,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "grid.color": GRID,
            "grid.linewidth": 0.7,
            "xtick.color": INK_2,
            "ytick.color": INK_2,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "xtick.major.size": 0,
            "ytick.major.size": 0,
            "legend.frameon": False,
            "legend.fontsize": 8.5,
            "figure.facecolor": PAPER,
            "savefig.facecolor": PAPER,
            "savefig.dpi": DPI,
            "savefig.bbox": "tight",
            "lines.linewidth": 2.0,
            "lines.markersize": 6,
            "text.color": INK,
            "pdf.fonttype": 42,
        }
    )
    _applied = True


def save(fig, path: Path) -> None:
    """Save as PNG with dpi=200 and no metadata."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=DPI, metadata={"Software": None})
    plt.close(fig)
