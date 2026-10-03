"""Figure 1: one figure, full text width, two stacked panels.

Run from the root of the supplement:  python code/make_fig1.py
Inputs:  data/tally.csv and data/model_report_dates.csv (release month, group and variant flags of every coded
         model-report row). Optional arguments replace the defaults: tally, dates file, file stem, output folder.
Outputs: output/figure1.pdf, output/figure1.svg, output/figure1.png, output/figure1_values_a.csv, output/figure1_values_b.csv

Both panels plot the headline reading, every event that reports a model's score (unit_status score or plotted);
rows that report no model score (not_score, no_numeral) are left out of both panels. The values CSVs carry the
printed-only and all-rows readings beside it.

Visual language: 5.5 x 3.1 in, the NeurIPS text width; 7.5 pt Helvetica, with Arial
or the metric-compatible Liberation Sans as fallbacks; greys by document class; Okabe-Ito vermillion #D55E00 as the
one accent colour (share line, markers, right axis); values above the bars. The share line is broken at the
leaderboard class (two events from one post), whose point is an open marker labelled "not compared". Every plotted
number is computed here from the two CSVs.
(a) mean of K2..K7 per event and share with none, by class; model reports split at June 2024 by the `group`
    column (the 'contemporaneous' June 2024 events, the Claude 3.5 addendum, are in neither bar).
(b) post-June-2024 model-report events that report the original English MMLU (orig_mmlu = 1), headline reading.
"""
import os
import sys
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

TALLY = sys.argv[1] if len(sys.argv) > 1 else "data/tally.csv"
EVENTS = sys.argv[2] if len(sys.argv) > 2 else "data/model_report_dates.csv"
STEM = sys.argv[3] if len(sys.argv) > 3 else "figure1"
OUT = sys.argv[4] if len(sys.argv) > 4 else "output"
K = ["K2", "K3", "K4", "K5", "K6", "K7"]
READ = {"headline": {"score", "plotted"}, "printed": {"score"}, "all_rows": {"score", "plotted", "not_score", "no_numeral"}}
GREY = {"C1": "#4d4d4d", "C2": "#4d4d4d", "C3": "#9e9e9e", "C4": "#cfcfcf", "C5": "#9e9e9e"}
LEFT_TOP = 3.0
RED_TOP = 75    # right-axis maximum (%), fixed for the published figure; recheck whenever the maximum share changes
FS = 7.5        # every label is 7.5 pt at print size

mpl.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Helvetica", "Arial", "Liberation Sans", "DejaVu Sans"],
    "pdf.fonttype": 42, "svg.fonttype": "none", "svg.hashsalt": "figure1", "ps.fonttype": 42, "font.size": FS, "axes.labelsize": FS,
    "xtick.labelsize": FS, "ytick.labelsize": FS, "axes.linewidth": 0.8,
    "xtick.major.width": 0.8, "ytick.major.width": 0.8, "axes.spines.top": False,
})


def load():
    t = pd.read_csv(TALLY)
    t = t[t.unit_status.notna()].copy()       # the one row without a unit_status records a document with no MMLU score
    assert t[K].notna().all().all(), "a coded row has a blank K code"
    t["k"] = t[K].astype(float).sum(axis=1)
    assert t.unit_status.isin(READ["all_rows"]).all(), "every row needs a unit_status"
    d = pd.read_csv(EVENTS)                   # model-report rows: dates, groups and variant flags, joined to their codes
    e = d.merge(t[["row", "doc_id", "location", "unit_status"] + K + ["k"]], on=["row", "doc_id", "location"],
                how="left", indicator=True, validate="one_to_one")
    assert (e._merge == "both").all(), "rows of the dates file missing from the tally"
    e = e.drop(columns="_merge")
    assert (e[K].astype(float).sum(axis=1) - e.k).abs().max() < 1e-9
    assert sorted(e.row) == sorted(t[t["class"] == "C3"].row), "tally C3 rows missing from the dates file"
    return t, e


def stats(d):
    return dict(n=len(d), mean_k2_k7=d.k.mean(), n_none=int((d.k == 0).sum()), share_none=(d.k == 0).mean())


def values_a(t, e, reading="headline"):
    t, e = t[t.unit_status.isin(READ[reading])], e[e.unit_status.isin(READ[reading])]
    spec = [("C1", "Construction\npaper", None, t[t["class"] == "C1"]),
            ("C2", "Repair\npapers", None, t[t["class"] == "C2"]),
            ("C3", "Before\nJune 2024", "pre", e[e.group == "pre"]),
            ("C3", "After\nJune 2024", "post", e[e.group == "post"]),
            ("C4", "Leaderboard\nposts", None, t[t["class"] == "C4"]),
            ("C5", "Governance\nsyntheses", None, t[t["class"] == "C5"])]
    return pd.DataFrame([dict(reading=reading, cls=c, bar=b, group=g or "", **stats(d)) for c, b, g, d in spec])


def values_b(e):
    o = e[(e.group == "post") & (e.orig_mmlu == 1)]
    out = []
    for reading, d in [("headline (plotted): events that report a model's score", o[o.unit_status.isin(READ["headline"])]),
                       ("printed only (not plotted)", o[o.unit_status.isin(READ["printed"])]),
                       ("all coded rows (not plotted)", o)]:
        for row, c in [("Repaired variant printed at the same event", int(d.repaired_variant.sum())),
                       ("Item-error qualification attached", int(d.K4.sum())),
                       ("No qualification at all", int((d.k == 0).sum()))]:
            out.append(dict(reading=reading, row=row, count=c, of=len(d)))
    return pd.DataFrame(out)


ACCENT = "#D55E00"                                   # Okabe-Ito vermillion, the one accent colour
LABEL = {"Leaderboard\nposts": "Leaderboard\npost"}
NOT_COMPARED = {"C4"}                                # classes too small for the comparison (the caption's rule)


def draw(va, vb, red_top=RED_TOP, left_top=LEFT_TOP, width=5.5, height=3.1, fs=7.5):
    from matplotlib.transforms import offset_copy
    import numpy as np
    fig = plt.figure(figsize=(width, height))
    L, W = 0.115, 0.765
    ax = fig.add_axes([L, 1.50 / height, W, 1.42 / height])
    bx = fig.add_axes([L, 0.06 / height, 0.30, 0.46 / height])
    xs = np.array([0, 1, 2.1, 3.1, 4.2, 5.2])
    ax.bar(xs, va.mean_k2_k7, width=0.72, color=[GREY[c] for c in va.cls], zorder=2)
    ax.set_xticks(xs); ax.set_xticklabels([]); ax.tick_params(axis="x", length=0)
    ax.set_xlim(-0.55, xs[-1] + 0.55)
    base = ax.get_xaxis_transform()
    for x, b, n in zip(xs, va.bar, va.n):
        tr = offset_copy(base, fig=fig, x=0, y=-19, units="points")
        ax.text(x, 0, f"{LABEL.get(b, b)}\n(n = {n})", transform=tr, ha="center", va="top", fontsize=fs, linespacing=1.15)
    mid = (xs[2] + xs[3]) / 2
    ax.text(mid, 0, "Model reports", transform=offset_copy(base, fig=fig, x=0, y=-3, units="points"), ha="center", va="top", fontsize=fs)
    x0, x1 = xs[2] - 0.36, xs[3] + 0.36
    tl = offset_copy(base, fig=fig, x=0, y=-14, units="points"); tt = offset_copy(base, fig=fig, x=0, y=-17, units="points")
    ax.plot([x0, x1], [0, 0], transform=tl, color="black", lw=0.6, clip_on=False, solid_capstyle="butt")
    for xx in (x0, x1):
        ax.annotate("", xy=(xx, 0), xycoords=tt, xytext=(xx, 0), textcoords=tl,
                    arrowprops=dict(arrowstyle="-", lw=0.6, color="black", shrinkA=0, shrinkB=0), annotation_clip=False)
    ax.set_ylim(0, left_top); ax.set_yticks([v for v in range(0, 4) if v <= left_top])
    ax.set_ylabel("Mean qualifications\nper event (of six)", fontsize=fs)
    ax.text(-0.13, 1.02, "(a)", transform=ax.transAxes, fontsize=fs, fontweight="bold", va="bottom")
    ax2 = ax.twinx()
    share = va.share_none.to_numpy() * 100
    comp = ~va.cls.isin(NOT_COMPARED).to_numpy()
    # the line joins only neighbouring comparable classes; it is broken at the leaderboard class
    for i in range(len(xs) - 1):
        if comp[i] and comp[i + 1]:
            ax2.plot(xs[i:i + 2], share[i:i + 2], color=ACCENT, lw=1.4, zorder=5, solid_capstyle="round")
    for x, v in zip(xs, va.mean_k2_k7):
        ax2.annotate(f"{v:.2f}", xy=(x, v), xycoords=ax.transData, xytext=(0, 4.5), textcoords="offset points",
                     ha="center", va="bottom", fontsize=fs, zorder=6, bbox=dict(boxstyle="square,pad=0.1", fc="white", ec="none"))
    ax2.plot(xs[comp], share[comp], ls="none", marker="o", ms=4, color=ACCENT, mec="white", mew=1.0, zorder=7)
    ax2.plot(xs[~comp], share[~comp], ls="none", marker="o", ms=4, mfc="white", mec=ACCENT, mew=1.0, zorder=7)
    for x, v in zip(xs[~comp], share[~comp]):
        ax2.annotate("not compared", xy=(x, v), xytext=(0, 5), textcoords="offset points", ha="center", va="bottom",
                     fontsize=fs, color=ACCENT, linespacing=0.95, zorder=8)
    ax2.set_ylim(0, red_top)
    ax2.set_yticks(list(range(0, red_top + 1, {40: 10, 45: 15, 50: 10, 60: 20, 75: 25, 80: 20}.get(red_top, 20))))
    ax2.set_ylabel("Events with no\nqualification (%)", color=ACCENT, fontsize=fs)
    ax2.tick_params(axis="y", colors=ACCENT, labelsize=fs); ax2.spines["right"].set_color(ACCENT)
    ax2.spines["top"].set_visible(False)
    for a in (ax, ax2): a.tick_params(axis="y", labelsize=fs)
    p = vb[vb.reading.str.startswith("headline")].reset_index(drop=True)
    n = int(p["of"].iloc[0]); y = [2, 1, 0]
    bx.barh(y, [n] * 3, height=0.62, color="white", edgecolor=GREY["C3"], lw=0.8, zorder=1)
    bx.barh(y, p["count"], height=0.62, color=GREY["C3"], zorder=2)
    for yy, c, lab in zip(y, p["count"], p.row):
        bx.text(n * 1.03, yy, f"{c} of {n}", va="center", ha="left", fontsize=fs)
        bx.text(n * 1.36, yy, lab, va="center", ha="left", fontsize=fs)
    bx.set_xlim(0, n); bx.set_ylim(-0.5, 2.5); bx.set_xticks([]); bx.set_yticks([])
    for s in ["left", "right", "top", "bottom"]: bx.spines[s].set_visible(False)
    fig.text(L - 0.13 * W, 0.70 / height, "(b)", fontsize=fs, fontweight="bold", va="top")
    fig.text(L, 0.70 / height, f"Model-report events after June 2024 that report the original English MMLU (n = {n})", fontsize=fs, va="top")
    for ext in ("pdf", "svg"):
        fig.savefig(f"{OUT}/{STEM}.{ext}")
    fig.savefig(f"{OUT}/{STEM}.png", dpi=300)
    fig._panels = (ax, ax2, bx)
    return fig


def main():
    os.makedirs(OUT, exist_ok=True)
    t, e = load()
    va, vb = values_a(t, e), values_b(e)
    allr = pd.concat([values_a(t, e, r) for r in READ])
    allr.assign(bar=allr.bar.map(lambda b: LABEL.get(b, b)).str.replace("\n", " ")).to_csv(f"{OUT}/{STEM}_values_a.csv", index=False)
    vb.to_csv(f"{OUT}/{STEM}_values_b.csv", index=False)
    return draw(va, vb), va, vb


if __name__ == "__main__":
    main()
