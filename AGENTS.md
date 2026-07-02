# StrideLab — Agent Guide

Markerless running gait & fatigue analysis from a **single side-mounted (sagittal) Intel RealSense camera**.
This file is the durable mental model for the project — read it first each session.

> If you want this auto-loaded by Claude Code every session, copy/rename it to `CLAUDE.md`
> (Claude Code auto-loads `CLAUDE.md`; other agents read `AGENTS.md`).

---

## 1. Pipeline at a glance

```
recorder.py ──► .bin recording ──► workbench.py (Streamlit) ──► Data Quality / Gait / Fatigue tabs
   (camera)      (binary frames)        core/workbench_main.py  (UI)
                                        core/workbench_logic.py (all math + IO)
```

- **`recorder.py`** — RealSense capture. Per frame writes each joint as `x,y,z` (3D meters, depth-based)
  **and** `px,py` (integer image pixels). Metadata header is JSON (camera + mediapipe settings).
- **`core/pose.py`** — MediaPipe Pose wrapper. Returns 33 landmarks in pixels. **No per-joint confidence
  is stored**, and the recorder **silently drops any joint with no valid depth** → gaps/zeros downstream.
- **`core/workbench_logic.py`** — the engine: `.bin`/`.csv` readers, `df_to_session`, DSP pipeline,
  kinematics, baseline/fatigue math. **All calculation lives here.**
- **`core/workbench_main.py`** — Streamlit UI only (plots, controls). No new math should live here.
- **`workbench.py`** — launcher (spawns Streamlit; handles frozen/PyInstaller paths).

Run it: `python workbench.py` (opens http://localhost:8501). The **user runs and tests themselves** —
hand off bug-free code; do not build heavy test scaffolding (see `memory/no-heavy-testing.md`).

Env: Windows / PowerShell primary, `venv/` in repo. Bash tool available for POSIX scripts.

---

## 2. The data reliability constraints (the most important section)

It is a **single profile camera**. This dictates what is trustworthy — respect it or you produce noise:

- **Reliable:** near-side, in-plane (sagittal) pixel signals — **trunk lean**, **head lean**,
  **pelvis vertical bounce / cadence**, **fore-aft (anteroposterior) pelvis position**, near-side arm swing.
- **Unreliable:** anything needing **left-vs-right** separation. In profile the **far limb is occluded and
  MediaPipe guesses it**, so `l_sho` vs `r_sho` and `l_elb` vs `r_elb` are largely noise. Do not default to them.
- **Out of plane / not measurable:** medio-lateral motion (strongest variability fatigue marker in the
  literature, but a side camera cannot see it — ignore it, don't fake it).
- **Measurement noise floor ≈ 3–5° RMSE** for markerless 2D sagittal joint angles. **A deviation smaller
  than the baseline SD / ~3–5° is within noise and must not be presented as real.**

Metrics are computed from **pixels (`px,py`)**, not the 3D world coords — depth on a single side camera is
noisy, so `_get_vec2d` (pixels) is the trustworthy path. The pixel-vs-world source is chosen **once per joint
at load time** in `df_to_session` (never mixed per-frame).

---

## 3. The metric engine — every metric is the same 5-step shape

Once you understand one, you understand all of them:

1. **Pick 2–3 landmark pixels** (e.g. hips + shoulders).
2. **One bit of 2D geometry** — a midpoint, an angle from vertical, or an interior angle between two vectors.
3. → **one number per frame.**
4. **Average over a time window** (per second / per minute / baseline window).
5. **Difference the windows** (later window − baseline) → the reported change.

| Metric | Points | Geometry | Reliable on side cam? |
|---|---|---|---|
| `trunk_lean` | hip-mid, shoulder-mid | angle of line from vertical | ✅ primary fatigue marker |
| `head_lean` | shoulder-mid, nose | angle of line from vertical | ✅ secondary |
| `l_sho`/`r_sho` | hip, shoulder, elbow | interior angle at shoulder | ⚠️ L/R occlusion |
| `l_elb`/`r_elb` | shoulder, elbow, wrist | interior angle at elbow (arm bend) | ⚠️ L/R occlusion |
| `com_x` | hip-mid | x-pixel ÷ torso length (fore-aft position) | ✅ (in-plane) |
| `vert_osc` | hip-mid | y-pixel ÷ torso length (vertical position) | ✅ (in-plane) |

Distances are normalized by **`session_torso_length`** (median hip-mid→shoulder-mid pixel length) so they
compare across subjects and camera distances. Cadence comes from an **FFT of the vertical pelvis signal**
(`compute_cadence`); slow positional drift from a low-passed linear fit (`compute_drift`).

To *see* a number get built end-to-end, construct `Frame`/`Joint` objects and call the real functions
(`_hip_mid2d`, `calculate_trunk_lean`, …) and print intermediates — that is the "glass box" trace.

---

## 4. Fatigue Analysis — design decisions (deliberate, don't regress these)

Mental model: **Fatigue = how far running posture has drifted from a fresh baseline, in real units (degrees).**

- **Deviation is reported as `delta` in the metric's own units** (e.g. `trunk_lean +3.3°`), *not* z-scores.
  z-scores were removed because a very steady baseline collapses `baseline_std → ~0` and makes them explode.
  `% change` is available as a secondary toggle.
- **Default tracked metrics = `RELIABLE_FATIGUE_METRICS` (`trunk_lean`, `head_lean`)**. The L/R arm angles are
  selectable but off by default and flagged as unreliable. `com_x` is excluded from fatigue (different units).
- **Baseline window is manual** (user picks a settled, unfatigued span; this matches the pre/post design used
  in the literature). Everything after is compared against it.
- **`compute_fatigue_curve` drops thin bins** via `min_frames` (UI passes `0.5 * bin_sec * fps`) so a sliver at
  an exclusion boundary or the session tail can't produce a wild Δ.

Key functions: `build_time_mask` (exclude regions) → `compute_baseline` (window mean/SD/n) →
`compute_fatigue_curve` (per-bin `mean, delta, pct_change, n`).

---

## 5. Literature grounding (for reliability + future direction)

- **Trunk forward-lean increase = the most validated running-fatigue kinematic** — keep it primary.
- **Second robust, direction-unambiguous signature: variability rises with fatigue** (stride-to-stride SD/CV,
  reduced regularity, higher sample entropy). Fore-aft (AP) variability is in-plane → measurable here;
  medio-lateral is not.
- The pre/post baseline design (fresh window vs later window) is standard methodology — the current workflow
  is correct, not naive.

References (PMC): trunk accelerometry CoM fatigue `PMC4627812`; stride variability post-exhaustion `PMC8181123`;
ML fatigue from IMUs `PMC8156769`; smartphone 2D running kinematics accuracy (~3–5°) `PMC11819925`.

---

## 6. Candidate next work (not yet built)

1. **Noise-floor band on the fatigue plot** — shade ±(baseline SD / ~3–5°) and grey-out Δ within it, so every
   number carries a trust level. *Highest leverage, smallest change.*
2. **Variability / consistency track** — within-bin SD (or CV) of `trunk_lean` and fore-aft pelvis position,
   plus stride-time variability from vertical-oscillation peaks. A second, always-increasing fatigue signal.
3. **"Inspect a frame" panel** — draw the stick figure, highlight the joints a metric uses, show the live
   midpoint→line→angle arithmetic next to the plotted value. Makes the app self-explaining (glass box).
4. **Gait-section reliability pass** — `build_summary`'s `peak_vel` is dominated by single-frame tracking
   glitches; the L/R arm split has the same occlusion problem as fatigue had.

---

## 7. Conventions

- New math → `workbench_logic.py`; UI-only → `workbench_main.py`. Keep them separated.
- Prefer **pixel-space (2D sagittal)** signals; treat 3D/world coords as noisy.
- Don't present a number the camera geometry can't support (L/R split, medio-lateral, sub-noise-floor Δ).
- User tests interactively; deliver working code, not test suites.
