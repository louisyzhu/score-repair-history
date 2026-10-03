"""Recompute every count-derived number that the main text and Appendix C of "Position: A Score Should Travel
With Its Repair History" print, from the files in data/ alone.

Run from the root of the supplement:

    python code/compute_summary.py

The script prints each number at the precision the paper uses, rounding half up, and writes every value at full
precision, beside its printed form, to output/summary_values.csv. Numbers that come from the sources themselves
(page anchors and quoted figures) are not recomputed here.

Units. A reporting event is a coded row whose unit_status is score or plotted (the headline reading). The six
substantive qualifications are K2 to K7, and an event's count k is their sum. Model reports are split at June
2024 by the group column of model_report_dates.csv. The one row with no unit_status records a release document
that prints no MMLU-family score and enters no statistic.

Uncertainty. Documents are resampled with replacement within each class (a stratified cluster bootstrap), and
model reports also within the groups before and after June 2024, with 10,000 replicates and seed 20261002. Each
stratum (the five classes, the two timing groups and the HLE documents) draws from its own random stream, spawned
from the seed in a fixed order, so the intervals are reproducible and a change in one class leaves the intervals of
the others unchanged. Counts of zero get exact (Clopper-Pearson) 95% intervals.
"""
import os
from decimal import Decimal, ROUND_HALF_UP

import numpy as np
import pandas as pd
from scipy.stats import beta

DATA, OUT = "data", "output"
K = ["K2", "K3", "K4", "K5", "K6", "K7"]          # the six substantive qualifications
K17 = ["K1"] + K
STATUS = {"score", "plotted", "not_score", "no_numeral"}
HEAD = {"score", "plotted"}
SEED, R = 20261002, 10000
CLASS_NAME = {"C1": "Construction paper", "C2": "Repair papers", "C3": "Model reports", "C4": "Leaderboard post",
              "C5": "Governance syntheses"}
RECORDS = []


# ------------------------------------------------------------------ printing and recording
def r(x, nd=2):
    """Round half up at nd decimals, from the shortest decimal form of x."""
    q = Decimal(1).scaleb(-nd) if nd else Decimal(1)
    s = str(Decimal(repr(float(x))).quantize(q, rounding=ROUND_HALF_UP))
    return s[1:] if s.startswith("-") and set(s[1:]) <= set("0.") else s


def pct(x, nd=0):
    return r(100 * x, nd) + "%"


def plain(v):
    """a value as text at full precision (floats in their shortest exact decimal form)"""
    if isinstance(v, tuple):
        return "(" + ", ".join(plain(x) for x in v) + ")"
    if isinstance(v, np.generic):
        v = v.item()
    return repr(v) if isinstance(v, float) else str(v)


def rec(section, quantity, value, printed):
    RECORDS.append(dict(section=section, quantity=quantity, value=plain(value), printed=printed))


def head(title):
    print(f"\n{title}\n{'=' * len(title)}")


def say(section, label, value, printed):
    rec(section, label, value, printed)
    print(f"  {label}: {printed}")


def nof(n, word):
    return f"{n} {word}" + ("" if n == 1 else "s")


def native(v):
    return v.item() if isinstance(v, np.generic) else v


def table(section, df, fmts, name):
    """Print a table and record each cell; fmts maps a column to the function that prints its values."""
    shown = pd.DataFrame({c: [fmts.get(c, str)(v) for v in df[c]] for c in df.columns}, index=df.index)
    for i in df.index:
        for c in df.columns:
            rec(section, f"{name} | {i} | {c}", native(df.loc[i, c]), shown.loc[i, c])
    print("\n".join("  " + x for x in shown.to_string().split("\n")))


# ------------------------------------------------------------------ data
def load_tally(name):
    t = pd.read_csv(f"{DATA}/{name}")
    null = t.unit_status.isna()
    assert null.sum() == 1, "exactly one row (a document with no MMLU-family score) has no unit_status"
    t = t[~null].copy()
    assert t[K17].notna().all().all(), "a coded row has a blank K code"
    assert not t.duplicated(["doc_id", "location"]).any(), "duplicate (doc_id, location)"
    assert t.unit_status.isin(STATUS).all()
    t[K17] = t[K17].astype(int)
    t["k"] = t[K].sum(axis=1)
    return t, null.sum()


dates = pd.read_csv(f"{DATA}/model_report_dates.csv")


def with_dates(t, final=True):
    m = t.merge(dates.drop(columns=["document"]), on="row", how="left", suffixes=("", "_d"), validate="one_to_one")
    c3 = m["class"] == "C3"
    assert m.loc[c3, "group"].notna().all() and m.loc[~c3, "group"].isna().all(), "model_report_dates.csv does not match"
    assert (m.loc[c3, "doc_id"] == m.loc[c3, "doc_id_d"]).all()
    if final:                                   # the dates file carries the final locations
        assert (m.loc[c3, "location"] == m.loc[c3, "location_d"]).all()
    return m.drop(columns=["doc_id_d", "location_d"])


t, n_null = load_tally("tally.csv")
t = with_dates(t)
t1, _ = load_tally("tally_first_pass.csv")
t1 = with_dates(t1, final=False)
assert (t1.row.values == t.row.values).all() and (t1.unit_status.values == t.unit_status.values).all()
for c in ["K5", "K6"]:                                   # the wording codes sit only where the code is 1
    w = t[c + "_wording"]
    assert w[t[c] == 1].notna().all() and w[t[c] == 0].isna().all() and w.dropna().isin([0, 1]).all()
h = t[t.unit_status.isin(HEAD)].copy()
h1 = t1[t1.unit_status.isin(HEAD)].copy()
full = pd.read_csv(f"{DATA}/tally.csv")
null_doc = full.loc[full.unit_status.isna(), "document"].iloc[0]

# ------------------------------------------------------------------ readings (the logic of the readings script)
BARS = [("Construction paper", lambda d: d["class"] == "C1"),
        ("Repair papers", lambda d: d["class"] == "C2"),
        ("Model reports, all", lambda d: d["class"] == "C3"),
        ("Model reports, before June 2024", lambda d: (d["class"] == "C3") & (d.group == "pre")),
        ("Model reports, after June 2024", lambda d: (d["class"] == "C3") & (d.group == "post")),
        ("Leaderboard post", lambda d: d["class"] == "C4"),
        ("Governance syntheses", lambda d: d["class"] == "C5")]


def stats(d, doc_weighted=False):
    if doc_weighted:
        return dict(n=len(d), docs=d.doc_id.nunique(), mean=d.groupby("doc_id").k.mean().mean(),
                    none=int((d.k == 0).sum()), share_none=(d.k == 0).groupby(d.doc_id).mean().mean())
    return dict(n=len(d), docs=d.doc_id.nunique(), mean=d.k.mean(), none=int((d.k == 0).sum()),
                share_none=(d.k == 0).mean())


def stated_only(d):
    d = d.copy()
    for c in ["K5", "K6"]:
        d[c] = d[c + "_wording"].fillna(d[c]).astype(int)
    d["k"] = d[K].sum(axis=1)
    return d


def no_k5k6(d):
    d = d.copy()
    d[["K5", "K6"]] = 0
    d["k"] = d[K].sum(axis=1)
    return d


def panel_b(d):
    o = d[(d["class"] == "C3") & (d.group == "post") & (d.orig_mmlu == 1)]
    return dict(events=len(o), repaired_variant=int(o.repaired_variant.sum()), item_error=int(o.K4.sum()),
                none=int((o.k == 0).sum()), none_qwen2=int(((o.k == 0) & (o.doc_id == "qwen2024qwen2")).sum()))


READINGS = [("Headline", h, False), ("Stated only", stated_only(h), False), ("Documents weighted", h, True),
            ("K5 and K6 dropped", no_k5k6(h), False), ("Printed only", t[t.unit_status == "score"], False),
            ("Every row", t, False), ("Before adjudication", h1, False)]
RS = {name: {bar: stats(d[f(d)], dw) for bar, f in BARS} for name, d, dw in READINGS}

# ------------------------------------------------------------------ 1. corpus
S = "corpus"
head("1. Corpus and unit (Sections 1 and 3)")
say(S, "coded rows", len(t), f"{len(t)}")
say(S, "documents with coded rows", t.doc_id.nunique(), f"{t.doc_id.nunique()}")
say(S, "further rows recording a release document with no MMLU-family score", int(n_null), f"{n_null} ({null_doc})")
say(S, "reporting events (score or plotted)", len(h), f"{len(h)}")
say(S, "rows that report no model score", int((~t.unit_status.isin(HEAD)).sum()),
    f"{int((~t.unit_status.isin(HEAD)).sum())} (not_score {int((t.unit_status == 'not_score').sum())}, "
    f"no_numeral {int((t.unit_status == 'no_numeral').sum())})")
say(S, "printed scores (score)", int((t.unit_status == "score").sum()), f"{int((t.unit_status == 'score').sum())}")
for c, nm in CLASS_NAME.items():
    say(S, f"documents with events, {nm.lower()}", h[h["class"] == c].doc_id.nunique(), f"{h[h['class'] == c].doc_id.nunique()}")
fb = full.found_by.value_counts()
fbc = full[full.unit_status.notna()].found_by.value_counts()
say(S, "coded rows from the first pass", int(fbc["first pass"] + fbc["first pass, vendor documents added later"]),
    f"{int(fbc['first pass'] + fbc['first pass, vendor documents added later'])} ({int(fbc['first pass'])} in the primary "
    f"corpus, {int(fbc['first pass, vendor documents added later'])} from vendor documents added later)")
cs = full[full.found_by == "completeness search"]["class"].value_counts()
say(S, "rows the completeness searches added", int(fb["completeness search"]),
    f"{int(fb['completeness search'])} (" + ", ".join(f"{CLASS_NAME[c].lower()} {int(cs.get(c, 0))}" for c in CLASS_NAME) + ")")
say(S, "rows the later page checks added", int(fb.get("page check", 0)),
    f"{int(fb.get('page check', 0))} (" + ", ".join(f"{d} {n}" for d, n in
                                                full[full.found_by == "page check"].document.value_counts().items()) + ")")
sv = pd.read_csv(f"{DATA}/release_survey.csv")
say(S, "surveyed release documents that print an MMLU-family score", int((sv.mmlu_family_score == "Yes").sum()),
    f"{int((sv.mmlu_family_score == 'Yes').sum())} of {len(sv)}")

# ------------------------------------------------------------------ 2. headline by class
S = "headline"
head("2. Headline reading by class (Section 3, Figure 1a)")
A = pd.DataFrame(RS["Headline"]).T
A.index.name = "class"
shown = pd.DataFrame({"events": A.n.astype(int), "documents": A.docs.astype(int), "mean of six": A["mean"].map(r),
                      "with none": A.none.astype(int), "share with none": A.share_none.map(pct)})
for bar in A.index:
    rec(S, f"{bar} | events", int(A.loc[bar, "n"]), str(int(A.loc[bar, "n"])))
    rec(S, f"{bar} | documents", int(A.loc[bar, "docs"]), str(int(A.loc[bar, "docs"])))
    rec(S, f"{bar} | mean", A.loc[bar, "mean"], r(A.loc[bar, "mean"]))
    rec(S, f"{bar} | with none", int(A.loc[bar, "none"]), str(int(A.loc[bar, "none"])))
    rec(S, f"{bar} | share with none", A.loc[bar, "share_none"], pct(A.loc[bar, "share_none"]))
print("\n".join("  " + x for x in shown.to_string().split("\n")))
print("  (the Claude 3.5 Sonnet addendum, released in June 2024, sits in neither split of the model reports)")

# ------------------------------------------------------------------ 3. readings of Appendix C
S = "readings"
head("3. Readings (Appendix C): mean of the six qualifications per event, share with none in brackets")
cells = {}
for name, _, _ in READINGS:
    cells[name] = {bar: f"{r(v['mean'])} ({pct(v['share_none'])})" for bar, v in RS[name].items()}
    for bar, v in RS[name].items():
        rec(S, f"{name} | {bar} | mean", v["mean"], r(v["mean"]))
        rec(S, f"{name} | {bar} | share with none", v["share_none"], pct(v["share_none"]))
cells["Events, headline"] = {bar: str(v["n"]) for bar, v in RS["Headline"].items()}
cells["Events, printed only"] = {bar: str(v["n"]) for bar, v in RS["Printed only"].items()}
cells["Rows, every row"] = {bar: str(v["n"]) for bar, v in RS["Every row"].items()}
for name, key in [("Events, headline", "Headline"), ("Events, printed only", "Printed only"), ("Rows, every row", "Every row")]:
    for bar, v in RS[key].items():
        rec(S, f"{name} | {bar}", v["n"], str(v["n"]))
short = {"Construction paper": "Construction", "Repair papers": "Repair", "Model reports, all": "MR all",
         "Model reports, before June 2024": "MR before", "Model reports, after June 2024": "MR after",
         "Leaderboard post": "Leaderboard", "Governance syntheses": "Governance"}
W = pd.DataFrame(cells).T.rename(columns=short)
print("\n".join("  " + x for x in W.to_string().split("\n")))
print("\n  Fall in the mean from the repair papers to the model reports, 1 - C3/C2:")
falls = {}
for name, _, _ in READINGS:
    falls[name] = 1 - RS[name]["Model reports, all"]["mean"] / RS[name]["Repair papers"]["mean"]
    say(S, f"fall, {name}", falls[name], pct(falls[name]))
say(S, "range of the fall across the seven readings", (min(falls.values()), max(falls.values())),
    f"between {pct(min(falls.values()))} and {pct(max(falls.values()))}")
print("\n  Counts behind the table, as events / documents / events with none:")
cnt = {}
for name, _, _ in READINGS:
    cnt[name] = {}
    for bar, v in RS[name].items():
        cnt[name][short[bar]] = f"{v['n']} / {v['docs']} / {v['none']}"
        for fld in ["n", "docs", "none"]:
            rec(S, f"{name} | {bar} | {fld}", int(v[fld]), str(v[fld]))
print("\n".join("  " + x for x in pd.DataFrame(cnt).T.to_string().split("\n")))

# ------------------------------------------------------------------ 4. uncertainty (the logic of the uncertainty script)
S = "uncertainty"
head("4. Uncertainty for the headline reading (Section 3, Appendix C)")


def cp(x, n, a=0.05):
    lo = 0.0 if x == 0 else beta.ppf(a / 2, x, n - x + 1)
    hi = 1.0 if x == n else beta.ppf(1 - a / 2, x + 1, n - x)
    return lo, hi


hb = h.assign(bare=(h.k == 0).astype(int))
docs = hb.groupby(["class", "doc_id"]).agg(n=("k", "size"), s=("k", "sum"), b=("bare", "sum")).reset_index()
ev = hb[hb["class"] == "C3"]
grp = ev.groupby(["group", "doc_id"]).agg(n=("k", "size"), s=("k", "sum"), b=("bare", "sum")).reset_index()


def arrays(frame):
    return frame.n.to_numpy(float), frame.s.to_numpy(float), frame.b.to_numpy(float)


def bstats(n, s, b):
    """pooled mean, share with none, document-weighted mean"""
    return s.sum() / n.sum(), b.sum() / n.sum(), np.mean(s / n)


strata = {c: arrays(docs[docs["class"] == c]) for c in ["C1", "C2", "C3", "C4", "C5"]}
strata.update({g: arrays(grp[grp.group == g]) for g in ["pre", "post"]})
point = {k: bstats(*v) for k, v in strata.items()}
STREAMS = ["C1", "C2", "C3", "C4", "C5", "pre", "post", "HLE"]
RNG = {k: np.random.default_rng(q) for k, q in zip(STREAMS, np.random.SeedSequence(SEED).spawn(len(STREAMS)))}
draws = {k: np.empty((R, 3)) for k in strata}
for rep in range(R):
    for k, (n, s, b) in strata.items():
        i = RNG[k].integers(0, len(n), len(n))
        draws[k][rep] = bstats(n[i], s[i], b[i])
U = []


def add(name, est, dist, note=""):
    lo, hi = np.percentile(dist, [2.5, 97.5])
    U.append(dict(quantity=name, estimate=est, lo=lo, hi=hi, method="cluster bootstrap", note=note))


lab = {"C1": "construction paper", "C2": "repair papers", "C3": "model reports", "C4": "leaderboard post",
       "C5": "governance syntheses", "pre": "model reports before June 2024", "post": "model reports after June 2024"}
for k in strata:
    nd = len(strata[k][0])
    note = "one document: no between-document variation" if nd == 1 else f"{nd} documents"
    add(f"mean, {lab[k]}", point[k][0], draws[k][:, 0], note)
    add(f"share bare, {lab[k]}", point[k][1], draws[k][:, 1], note)
    add(f"document-weighted mean, {lab[k]}", point[k][2], draws[k][:, 2], note)
gap = 1 - draws["C3"][:, 0] / draws["C2"][:, 0]
add("gap, model reports below repair papers (share of repair-paper mean)", 1 - point["C3"][0] / point["C2"][0], gap,
    f"P(gap <= 0) = {np.mean(gap <= 0):.4f}")
gapw = 1 - draws["C3"][:, 2] / draws["C2"][:, 2]
add("gap, document-weighted", 1 - point["C3"][2] / point["C2"][2], gapw, f"P(gap <= 0) = {np.mean(gapw <= 0):.4f}")
gp = 1 - draws["post"][:, 0] / draws["C2"][:, 0]
add("gap, post-June-2024 reports below repair papers", 1 - point["post"][0] / point["C2"][0], gp,
    f"P(gap <= 0) = {np.mean(gp <= 0):.4f}")
gpw = 1 - draws["post"][:, 2] / draws["C2"][:, 2]
add("gap, post-June-2024 reports below repair papers, document-weighted", 1 - point["post"][2] / point["C2"][2], gpw,
    f"P(gap <= 0) = {np.mean(gpw <= 0):.4f}")
dpp = draws["post"][:, 0] - draws["pre"][:, 0]
add("difference in mean, after minus before June 2024", point["post"][0] - point["pre"][0], dpp,
    f"P(diff > 0) = {np.mean(dpp > 0):.4f}")
dppw = draws["post"][:, 2] - draws["pre"][:, 2]
add("difference in document-weighted mean, after minus before June 2024", point["post"][2] - point["pre"][2], dppw,
    f"P(diff > 0) = {np.mean(dppw > 0):.4f}")
# HLE: the nine documents, resampled on their own stream
hl0 = pd.read_csv(f"{DATA}/hle_tally.csv")
for c in K17:
    hl0[c] = hl0[c].astype(int)
hl0["k"] = hl0[K].sum(axis=1)
hl0["bare"] = (hl0.k == 0).astype(int)
hdocs = hl0.groupby("doc_id").agg(n=("k", "size"), s=("k", "sum"), b=("bare", "sum")).reset_index()
hn, hs, hbb = arrays(hdocs)
hpoint = bstats(hn, hs, hbb)
hdraw = np.empty((R, 3))
for rep in range(R):
    i = RNG["HLE"].integers(0, len(hn), len(hn))
    hdraw[rep] = bstats(hn[i], hs[i], hbb[i])
add("mean, HLE events", hpoint[0], hdraw[:, 0], f"{len(hn)} documents")
add("share bare, HLE events", hpoint[1], hdraw[:, 1], f"{len(hn)} documents")
c3h = h[h["class"] == "C3"]
for name, x, n in [("item error at model-report events", int(c3h.K4.sum()), len(c3h)),
                   ("item error at model-report events, documents with any",
                    int((c3h.groupby("doc_id").K4.max() > 0).sum()), c3h.doc_id.nunique()),
                   ("saturation at model-report events", int(c3h.K7.sum()), len(c3h)),
                   ("saturation at model-report events, documents with any",
                    int((c3h.groupby("doc_id").K7.max() > 0).sum()), c3h.doc_id.nunique())]:
    lo, hi = cp(x, n)
    U.append(dict(quantity=name, estimate=x / n, lo=lo, hi=hi, method="exact (Clopper-Pearson)", note=f"{x} of {n}"))
hl = pd.read_csv(f"{DATA}/hle_tally.csv")
for c in K17:
    hl[c] = hl[c].astype(int)
hl["k"] = hl[K].sum(axis=1)
for name, x, n in [("HLE item error, events", int(hl.K4.sum()), len(hl)),
                   ("HLE item error, documents with any", int((hl.groupby("doc_id").K4.max() > 0).sum()),
                    hl.doc_id.nunique())]:
    lo, hi = cp(x, n)
    U.append(dict(quantity=name, estimate=x / n, lo=lo, hi=hi, method="exact (Clopper-Pearson)", note=f"{x} of {n}"))
U = pd.DataFrame(U)


def ufmt(q, v):
    """the paper prints means and differences to two decimals and shares and gaps as percentages"""
    return pct(v) if (q.startswith(("share", "gap")) or "error" in q or "saturation" in q) else r(v)


print(f"  {'quantity':<72} {'estimate':>8}  {'95% interval':<15} method; note")
for u in U.itertuples():
    e, lo, hi = ufmt(u.quantity, u.estimate), ufmt(u.quantity, u.lo), ufmt(u.quantity, u.hi)
    for fld, v, pv in [("estimate", u.estimate, e), ("lo", u.lo, lo), ("hi", u.hi, hi)]:
        rec(S, f"{u.quantity} | {fld}", float(v), pv)
    rec(S, f"{u.quantity} | note", u.note, u.note)
    print(f"  {u.quantity:<72} {e:>8}  {'[' + lo + ', ' + hi + ']':<15} {u.method}; {u.note}")

# ------------------------------------------------------------------ 5. item error, saturation, contamination
S = "qualifications"
head("5. Item error, saturation and contamination (Section 3)")
c2h, c5h = h[h["class"] == "C2"], h[h["class"] == "C5"]
ns = t[~t.unit_status.isin(HEAD)]
c3h1 = h1[h1["class"] == "C3"]
say(S, "item error at model-report events", int(c3h.K4.sum()), f"{int(c3h.K4.sum())} of {len(c3h)}")
say(S, "saturation at model-report events", int(c3h.K7.sum()), f"{int(c3h.K7.sum())} of {len(c3h)}")
say(S, "item error at model-report events, first pass", int(c3h1.K4.sum()), f"{int(c3h1.K4.sum())} of {len(c3h1)}")
say(S, "saturation at model-report events, first pass", int(c3h1.K7.sum()), f"{int(c3h1.K7.sum())} of {len(c3h1)}")
say(S, "contamination at model-report events", int(c3h.K3.sum()), f"{int(c3h.K3.sum())} of {len(c3h)}")
for x in c3h[c3h.K3 == 1].itertuples():
    print(f"      contamination at: {x.document}, {x.location}")
say(S, "item error at repair-paper events", int(c2h.K4.sum()), f"{int(c2h.K4.sum())} of {len(c2h)}")
say(S, "saturation at repair-paper events", int(c2h.K7.sum()), f"{int(c2h.K7.sum())} of {len(c2h)}")
say(S, "contamination at repair-paper events", int(c2h.K3.sum()), f"{int(c2h.K3.sum())} of {len(c2h)}")
say(S, "item error at score events, all classes", int(h.K4.sum()), f"{int(h.K4.sum())} of {len(h)}")
say(S, "item error at rows that report no model score", int(ns.K4.sum()), f"{int(ns.K4.sum())} of {len(ns)}")

# ------------------------------------------------------------------ 6. timing
S = "timing"
head("6. Model reports before and after June 2024 (Section 3, Appendix C)")
for g, nm in [("pre", "before June 2024"), ("post", "after June 2024"), ("contemporaneous", "in June 2024")]:
    d = c3h[c3h.group == g]
    say(S, f"events {nm}", len(d), f"{nof(len(d), 'event')} in {nof(d.doc_id.nunique(), 'report')}, mean {r(d.k.mean())}, "
        f"{int((d.k == 0).sum())} with none ({pct((d.k == 0).mean())})")
    rec(S, f"mean {nm}", d.k.mean(), r(d.k.mean()))
    rec(S, f"share with none {nm}", (d.k == 0).mean(), pct((d.k == 0).mean()))
pw = c3h.groupby(["group", "doc_id"]).k.mean().groupby("group").mean()
say(S, "mean of per-report means, before and after June 2024", (pw["pre"], pw["post"]),
    f"from {r(pw['pre'])} to {r(pw['post'])}")
post = c3h[c3h.group == "post"]
qw = post[post.doc_id.str.startswith("qwen")]
say(S, "later events from the two Qwen reports", len(qw), f"{len(qw)} of {len(post)}")
c2w = c2h.groupby("doc_id").k.mean().mean()
u = U.set_index("quantity")
g1 = u.loc["gap, post-June-2024 reports below repair papers"]
say(S, "later reports below the repair papers", g1.estimate, f"{pct(g1.estimate)} ([{pct(g1.lo)}, {pct(g1.hi)}])")
g2 = u.loc["gap, post-June-2024 reports below repair papers, document-weighted"]
say(S, "later reports below the repair papers, weighted by report", g2.estimate,
    f"{pct(g2.estimate)} below the repair papers' {r(c2w)} ([{pct(g2.lo)}, {pct(g2.hi)}])")
d1 = u.loc["difference in mean, after minus before June 2024"]
d2 = u.loc["difference in document-weighted mean, after minus before June 2024"]
say(S, "after minus before June 2024, event weighting", d1.estimate, f"{r(d1.estimate)} ([{r(d1.lo)}, {r(d1.hi)}])")
say(S, "after minus before June 2024, document weighting", d2.estimate, f"{r(d2.estimate)} ([{r(d2.lo)}, {r(d2.hi)}])")
say(S, "replicates in which the gap between repair papers and model reports exceeds zero", int((gap > 0).sum()),
    f"{int((gap > 0).sum()):,} of {R:,}")

# ------------------------------------------------------------------ 7. panel (b)
S = "panel_b"
head("7. Post-June-2024 model-report events on the original English MMLU (Sections 3 and 5, Figure 1b, Appendix C)")
PB = pd.DataFrame({name: panel_b(d) for name, d in [("Headline", h), ("Stated only", stated_only(h)),
                                                       ("K5 and K6 dropped", no_k5k6(h)),
                                                       ("Printed only", t[t.unit_status == "score"]), ("Every row", t)]}).T
table(S, PB.rename(columns={"repaired_variant": "repaired variant", "item_error": "item error",
                            "none_qwen2": "of which Qwen2"}), {}, "panel b")
c3a = t[t["class"] == "C3"]
pro = c3a[(c3a.group == "post") & c3a.location.str.contains(r"MMLU[- ]Pro")].doc_id.nunique()
say(S, "post-repair reports that print MMLU-Pro", pro, f"{pro} of {c3a[c3a.group == 'post'].doc_id.nunique()}")

# ------------------------------------------------------------------ 8. category shares
S = "shares"
head("8. Share of headline events carrying each qualification, by class (Appendix C)")
SH = h.groupby("class")[K].mean()
SH.insert(0, "events", h.groupby("class").size())
SH.index = [CLASS_NAME[c] for c in SH.index]
SH.columns = ["events", "implementation K2", "contamination K3", "item error K4", "aggregate K5", "scope K6",
              "saturation K7"]
table(S, SH, {c: pct for c in SH.columns[1:]}, "share")

# ------------------------------------------------------------------ 9. census of whole reports
S = "census"
head("9. Reports that state each qualification anywhere (Sections 3 and 5, Appendix C)")
cen = pd.read_csv(f"{DATA}/census.csv")
dlr = pd.read_csv(f"{DATA}/document_level_records.csv")
any_rows = []
for doc in c3a.sort_values("release_month").doc_id.unique():
    e = c3a[c3a.doc_id == doc]
    row_ = dict(doc_id=doc, group=e.group.iloc[0])
    for k in K:
        at_event = int(e[k].sum() > 0)
        record = bool(((dlr.doc_id == doc) & (dlr.category == k)).any())
        named = bool(((cen.doc_id == doc) & (cen.category == k) & (cen.concerns_mmlu_family == "yes")).any()) or record
        generic = bool(((cen.doc_id == doc) & (cen.category == k) & (cen.concerns_mmlu_family == "unclear")).any())
        row_[k + "_named"] = int(at_event or named)
        row_[k + "_incl_generic"] = int(at_event or named or generic)
    any_rows.append(row_)
AN = pd.DataFrame(any_rows)
ORDER = [("K2", "implementation"), ("K4", "item error"), ("K3", "contamination"), ("K7", "saturation"),
         ("K6", "scope"), ("K5", "aggregate")]
tab = {}
for g, nm in [("pre", "Before June 2024"), ("contemporaneous", "June 2024"), ("post", "After June 2024"), (None, "All")]:
    d = AN if g is None else AN[AN.group == g]
    lbl = f"{nm} ({len(d)})"
    tab[lbl] = {}
    for k, cn in ORDER:
        a, b = int(d[k + "_named"].sum()), int(d[k + "_incl_generic"].sum())
        tab[lbl][cn] = f"{a}" if a == b else f"{a} ({b})"
        rec(S, f"{lbl} | {cn} | named", a, str(a))
        rec(S, f"{lbl} | {cn} | with generic statements", b, str(b))
print("  Counts of reports; generic statements about all benchmarks added in brackets where they add reports.")
print("\n".join("  " + x for x in pd.DataFrame(tab).T.to_string().split("\n")))
say(S, "reports with an implementation statement somewhere", int(AN.K2_named.sum()), f"{int(AN.K2_named.sum())} of {len(AN)}")
say(S, "reports with an item-error qualification anywhere", int(AN.K4_named.sum()), f"{int(AN.K4_named.sum())} of {len(AN)}")
kk = c3h[(c3h.release_month > "2024-02") & (c3h.orig_mmlu == 1)]
say(S, "events on the English MMLU after KMMLU appeared (released after February 2024)", len(kk), f"{len(kk)}")
say(S, "of them with a scope qualification", int(kk.K6.sum()), f"{int(kk.K6.sum())}")
say(S, "of them with a scope qualification stated in words", int((kk.K6_wording == 1).sum()),
    f"{int((kk.K6_wording == 1).sum())}")

# ------------------------------------------------------------------ 10. governance syntheses
S = "governance"
head("10. Governance syntheses (Section 3)")
c5h1 = h1[h1["class"] == "C5"]
say(S, "events with no qualification", int((c5h.k == 0).sum()), f"{int((c5h.k == 0).sum())} of {len(c5h)}")
say(S, "events with no qualification before adjudication", int((c5h1.k == 0).sum()), f"{int((c5h1.k == 0).sum())} of {len(c5h1)}")
ai = c5h[c5h.doc_id == "aiindex2025"]
say(S, "AI Index 2025 events with no qualification", int((ai.k == 0).sum()), f"{int((ai.k == 0).sum())} of {len(ai)}")
gw = (c5h.k == 0).groupby(c5h.doc_id).mean().mean()
say(S, "share with none, each document weighted equally", gw, pct(gw))
print("  the events that carry a qualification:")
for x in c5h[c5h.k > 0].itertuples():
    print(f"      {x.document} | {x.location} | " + " ".join(f"{k}={getattr(x, k)}" for k in K if getattr(x, k)))

# ------------------------------------------------------------------ 11. reliability of the second coding
S = "reliability"
head("11. Second coding against the first pass, before adjudication (Section 3, Appendix B)")
log = pd.read_csv(f"{DATA}/adjudication_log.csv", dtype=str, keep_default_na=False)
dis = log[(log.stage == "adjudication") & log.field.isin(K17) & (log.before != "") & (log.second_coding != "")
          & (log.before != log.second_coding)]
sc = pd.read_csv(f"{DATA}/second_coding_cells.csv", dtype=str, keep_default_na=False)
coded2 = sorted(set(sc.row.astype(int)))                 # rows that went through the second coding
second = t1.set_index("row").loc[coded2, K17].copy()
for x in dis.itertuples():
    assert second.loc[int(x.row), x.field] == int(x.before)
    second.loc[int(x.row), x.field] = int(x.second_coding)
first = t1.set_index("row").loc[coded2, K17]
say(S, "rows in the second coding", len(coded2), f"{len(coded2)} of {len(t1)}")


def kappa(a, b):
    """Cohen's kappa; not defined (nan) when either coding gives every case the same code"""
    a, b = np.asarray(a), np.asarray(b)
    if len(set(a)) == 1 or len(set(b)) == 1:
        return float("nan")
    po = (a == b).mean()
    pe = sum((a == v).mean() * (b == v).mean() for v in set(a) | set(b))
    return (po - pe) / (1 - pe)


REL = pd.DataFrame({k: dict(first=int(first[k].sum()), second=int(second[k].sum()),
                            disagreements=int((first[k] != second[k]).sum()), kappa=kappa(first[k], second[k]))
                    for k in K17}).T
REL[["first", "second", "disagreements"]] = REL[["first", "second", "disagreements"]].astype(int)
table(S, REL.rename(columns={"first": "first pass positive", "second": "second coding positive"}),
      {"kappa": lambda v: "-" if pd.isna(v) else r(v)}, "reliability")
n6 = int(REL.loc[K, "disagreements"].sum())
cells6 = len(first) * len(K)
say(S, "disagreements on the six qualifications", n6, f"{n6} of {cells6:,} ({pct(n6 / cells6, 1)})")
kap = REL.loc[["K2", "K3", "K4", "K5", "K6"], "kappa"].astype(float)
say(S, "kappa range except saturation", (kap.min(), kap.max()), f"from {r(kap.min())} to {r(kap.max())}")
say(S, "kappa for saturation", float(REL.loc["K7", "kappa"]), r(REL.loc["K7", "kappa"]))
say(S, "disputed cells", len(dis), f"{len(dis)} ({n6} on the six qualifications and "
    f"{int(REL.loc['K1', 'disagreements'])} on variant identification)")
sk = sc[sc.category.isin(K17)]
for k in K17:                                            # the cells file and the log give the same second coding
    assert int((sk[sk.category == k].second_coding == "1").sum()) == int(REL.loc[k, "second"]), k
assert int((sk.first_pass != sk.second_coding).sum()) == len(dis)
say(S, "agents in the second coding", sc.coder_group.nunique(), f"{sc.coder_group.nunique()}")
fl = sc[sc.flagged == "1"].row.nunique()
say(S, "rows whose second coder declared a memory of project conventions", fl, f"{fl}")
final = t.set_index("row")[K17]
fol = sum(int(final.loc[int(x.row), x.field] == int(x.second_coding)) for x in dis.itertuples())
say(S, "disputed cells whose final code follows the second coding", fol,
    f"{fol} of {len(dis)}; {len(dis) - fol} follow the first pass")

# ------------------------------------------------------------------ 12. Humanity's Last Exam
S = "hle"
head("12. Humanity's Last Exam (Section 3, Appendix E)")
say(S, "events", len(hl), f"{len(hl)} in {hl.doc_id.nunique()} model releases")
say(S, "mean qualifications per event", hl.k.mean(), r(hl.k.mean()))
say(S, "events with none", int((hl.k == 0).sum()), f"{int((hl.k == 0).sum())} ({pct((hl.k == 0).mean())})")
say(S, "qualifications that state an implementation", int(hl.K2.sum()), f"{int(hl.K2.sum())} of {int(hl.k.sum())}")
say(S, "events with an item-error qualification", int(hl.K4.sum()), f"{int(hl.K4.sum())} of {len(hl)}")
hu = u.loc["HLE item error, documents with any"]
say(S, "exact 95% upper limit on the share of documents with item error", hu.hi, pct(hu.hi))
lk = pd.read_csv(f"{DATA}/hle_linked_documents.csv")
hc = pd.read_csv(f"{DATA}/hle_second_coding_cells.csv", dtype=str, keep_default_na=False)


def hcodes(col):
    p = hc[hc.category.isin(K17)].pivot(index="event_id", columns="category", values=col).astype(int)
    p.index = p.index.astype(int)
    return p.sort_index()[K17]


hfirst, hsecond = hcodes("first_pass"), hcodes("second_coding")
base = hl.set_index("event_id")[K17]
linked = base.copy()
for x in lk[lk.reading == "linked methodology document attached"].itertuples():
    assert linked.loc[x.event_id, x.category] == 0
    linked.loc[x.event_id, x.category] = 1
linked_k5 = linked.copy()
for x in lk[lk.reading == "possible aggregate addition"].itertuples():
    assert linked_k5.loc[x.event_id, x.category] == 0
    linked_k5.loc[x.event_id, x.category] = 1
say(S, "events with an item-error qualification if linked methodology documents are attached", int(linked.K4.sum()),
    f"{int(linked.K4.sum())} of {len(linked)}")


def hstats(codes, keep=None):
    d = hl.set_index("event_id")[["doc_id", "unit_status"]].join(codes)
    if keep is not None:
        d = d[d.unit_status.isin(keep)]
    k = d[K].sum(axis=1)
    return dict(events=len(d), mean=k.mean(), none=int((k == 0).sum()), share_none=(k == 0).mean(),
                docs=d.doc_id.nunique(), doc_mean=k.groupby(d.doc_id).mean().mean(),
                doc_share_none=(k == 0).groupby(d.doc_id).mean().mean())


HR = [("Headline (adjudicated)", hstats(base)), ("Printed scores only", hstats(base, {"score"})),
      ("Each document weighted equally", hstats(base)), ("Linked methodology documents attached", hstats(linked)),
      ("The same, with four possible aggregate additions", hstats(linked_k5)),
      ("First pass, before adjudication", hstats(hfirst)), ("Second coding alone", hstats(hsecond))]
print("  Readings (Appendix E): events, mean of the six qualifications, events with none")
for name, v in HR:
    if name.startswith("Each document"):
        e_, m_, n_ = f"{v['docs']} documents", r(v["doc_mean"]), pct(v["doc_share_none"])
        rec(S, f"reading | {name} | mean", v["doc_mean"], m_)
        rec(S, f"reading | {name} | share with none", v["doc_share_none"], n_)
    else:
        e_, m_, n_ = str(v["events"]), r(v["mean"]), f"{v['none']} ({pct(v['share_none'])})"
        rec(S, f"reading | {name} | mean", v["mean"], m_)
        rec(S, f"reading | {name} | with none", v["none"], str(v["none"]))
        rec(S, f"reading | {name} | share with none", v["share_none"], pct(v["share_none"]))
    rec(S, f"reading | {name} | events", e_, e_)
    print(f"    {name:<52} {e_:>12}  {m_:>5}  {n_}")
kc = hc[hc.category.isin(K17)]
ag = int((kc.first_pass == kc.second_coding).sum())
say(S, "cells on which the second coding agrees with the first", ag, f"{ag} of {len(kc)}")
for cat in K17 + ["hle_variant", "hle_variant_features"]:
    s_ = hc[hc.category == cat]
    a_ = int((s_.first_pass == s_.second_coding).sum())
    kp = kappa(s_.first_pass, s_.second_coding)
    say(S, f"agreement, {cat}", a_, f"{a_} of {len(s_)}" + ("" if np.isnan(kp) or a_ == len(s_) else f" (kappa {r(kp)})"))
say(S, "agents in the second coding", hc.coder_group.nunique(), f"{hc.coder_group.nunique()}")
uf = kc[kc.flagged == "0"]
say(S, "agreement on the unflagged events", int((uf.first_pass == uf.second_coding).sum()),
    f"{int((uf.first_pass == uf.second_coding).sum())} of {len(uf)} cells ({uf.event_id.nunique()} events)")

# ------------------------------------------------------------------ 13. population
S = "population"
head("13. The MMLU successor population (Sections 2 and 5, Appendix F)")
pop = pd.read_csv(f"{DATA}/population.csv")
pop = pop[pop.in_population == "yes"]
lay = pop.layer_repaired.value_counts()
say(S, "artefacts in the population", len(pop), f"{len(pop)}")
say(S, "artefacts that relocate the scope", int(lay["scope"]), f"{int(lay['scope'])}")
rep = int(lay["substrate"] + lay["object"] + lay["conditions"])
say(S, "artefacts that repair the items, the format or the conditions", rep,
    f"{rep} (substrate {int(lay['substrate'])}, object {int(lay['object'])}, conditions {int(lay['conditions'])})")
say(S, "artefacts that change no layer", int(lay["none"]), f"{int(lay['none'])}")
v1 = pd.to_datetime(pop.set_index("primary_reference_bibtex_key").arxiv_v1_date[["wang2024mmlupro", "gema2025redux"]])
days = int((v1["gema2025redux"] - v1["wang2024mmlupro"]).days)
say(S, "days between the first arXiv versions of MMLU-Pro and MMLU-Redux", days,
    f"{days} ({v1['wang2024mmlupro'].day} {v1['wang2024mmlupro']:%B %Y} and {v1['gema2025redux'].day} {v1['gema2025redux']:%B %Y})")

os.makedirs(OUT, exist_ok=True)
pd.DataFrame(RECORDS).to_csv(f"{OUT}/summary_values.csv", index=False)
print(f"\nWrote {OUT}/summary_values.csv ({len(RECORDS)} values).")
