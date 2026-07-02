import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from core import workbench_logic as logic

# =============================================================================
# 1. RESEARCH LOGIC
# =============================================================================

def load_dataset(uploaded_file):
    meta, df = logic.load_recording(uploaded_file.getvalue(), uploaded_file.name)
    return meta, df

@st.cache_data(show_spinner="Generating Biomechanical Report...")
def process_analysis_data(df_raw):
    session = logic.df_to_session(df_raw)
    ts_df, _ = logic.generate_analysis_report(session)
    ts_df['time_sec'] = np.floor(ts_df['timestamp']).astype(int)
    numeric_cols = [c for c in ts_df.columns if c not in ['frame', 'time_sec', 'timestamp', 'time_min']]
    df_sec = ts_df.groupby('time_sec')[numeric_cols].mean().reset_index()
    ts_df['time_min'] = np.floor(ts_df['timestamp'] / 60.0).astype(int)
    df_min = ts_df.groupby('time_min')[numeric_cols].mean().reset_index()

    # Distribution / ROM / peak angular velocity computed at frame level (accurate),
    # while the long-term drift (trend/min) is estimated from per-second means.
    stats_df = logic.build_summary(ts_df, session.fps)
    if len(df_sec) > 1:
        x_mins = df_sec['time_sec'] / 60.0
        for col in numeric_cols:
            mask = ~np.isnan(df_sec[col])
            if mask.sum() > 1:
                slope, _ = np.polyfit(x_mins[mask], df_sec[col][mask], 1)
                stats_df.loc[col, 'trend/min'] = slope

    # Session-level derived metrics (single values for this iteration).
    cadence, step_hz = logic.compute_cadence(ts_df['vert_osc'], session.fps)
    drift_net, drift_rate = logic.compute_drift(ts_df['com_x'], session.fps)
    derived = {
        'fps': session.fps,
        'cadence': cadence, 'step_hz': step_hz,
        'drift_net': drift_net, 'drift_rate': drift_rate,
        'torso_px': logic.session_torso_length(session),
    }
    return ts_df, df_sec, df_min, stats_df, derived

def create_kinematic_plot(df, x_col, y_cols, names, colors, title, show_env=False, show_trend=False, ylabel="Degrees (°)"):
    fig = go.Figure()
    # Dynamic window size from eval.py
    env_win = max(1, len(df)//20) if show_env else 1

    for y_col, name, color in zip(y_cols, names, colors):
        if y_col not in df.columns: continue
        x, y = df[x_col].values, df[y_col].values
        
        if show_env:
            m = df[y_col].rolling(env_win, min_periods=1).mean().values
            s = df[y_col].rolling(env_win, min_periods=1).std().fillna(0).values
            fig.add_trace(go.Scatter(x=x, y=m+s, mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
            fig.add_trace(go.Scatter(x=x, y=m-s, mode='lines', line=dict(width=0), fillcolor=f"rgba{tuple(int(color.lstrip('#')[i:i+2], 16) for i in (0,2,4)) + (0.2,)}", fill='tonexty', showlegend=False, hoverinfo='skip'))
            fig.add_trace(go.Scatter(x=x, y=m, mode='lines', name=name, line=dict(color=color, width=2.5)))
        else:
            fig.add_trace(go.Scatter(x=x, y=y, mode='lines', name=name, line=dict(color=color, width=2.5)))
        
        if show_trend:
            mask = ~np.isnan(y) & ~np.isnan(x)
            if mask.sum() > 1:
                slope, intercept = np.polyfit(x[mask], y[mask], 1)
                fig.add_trace(go.Scatter(x=x, y=slope*x+intercept, mode='lines', name=f"{name} Trend", line=dict(color=color, width=1.5, dash='dash'), hoverinfo='skip'))
    
    fig.update_layout(
        title=title, template="plotly_white", height=350, margin=dict(l=0, r=0, t=50, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_title=x_col.capitalize(), yaxis_title=ylabel, hovermode="x unified"
    )
    return fig

_FATIGUE_PALETTE = ["#005FB8", "#D83B01", "#8764B8", "#107C10", "#CA5010", "#5C2E91", "#038387"]

def create_fatigue_plot(fc, value_col, baseline_window=None, exclude_regions=None,
                        title="Posture Drift From Baseline", ylabel="Δ from baseline (°)"):
    """Per-bin deviation-from-baseline curve, one line per metric, with the
    baseline window and excluded regions shaded (x axis in minutes)."""
    fig = go.Figure()
    for i, metric in enumerate(sorted(fc['metric'].unique())):
        sub = fc[fc['metric'] == metric].sort_values('time_min')
        fig.add_trace(go.Scatter(
            x=sub['time_min'], y=sub[value_col], mode='lines+markers', name=metric,
            line=dict(color=_FATIGUE_PALETTE[i % len(_FATIGUE_PALETTE)], width=2)))
    fig.add_hline(y=0, line=dict(color=logic.COLOR_REF_LINE, dash='dash'))
    if baseline_window:
        fig.add_vrect(x0=baseline_window[0] / 60.0, x1=baseline_window[1] / 60.0,
                      fillcolor="rgba(16,124,16,0.10)", line_width=0,
                      annotation_text="baseline", annotation_position="top left")
    for region in (exclude_regions or []):
        a, b = region
        if a is None or b is None:
            continue
        fig.add_vrect(x0=min(a, b) / 60.0, x1=max(a, b) / 60.0,
                      fillcolor="rgba(0,0,0,0.06)", line_width=0)
    fig.update_layout(
        title=title, template="plotly_white", height=420, margin=dict(l=0, r=0, t=50, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_title="Time (min)", yaxis_title=ylabel, hovermode="x unified")
    return fig

# =============================================================================
# 2. MAIN INTERFACE
# =============================================================================

def main():
    st.set_page_config(page_title="Workbench", layout="wide")
    
    # Global Styles
    st.markdown("""
        <style>
            .block-container { padding-top: 1rem !important; }
            div[data-testid="stMetric"] {
                border: 1px solid #e9ecef;
                padding: 10px;
                border-radius: 5px;
            }
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

    # Header Row
    c1, c2 = st.columns([0.8, 0.2], vertical_alignment="bottom")
    with c1:
        st.header("Workbench")
    with c2:
        if st.button("Reset Workspace", type="secondary", use_container_width=True):
            for k in ['raw_df', 'clean_df', 'validation_report', 'recording_meta']:
                if k in st.session_state: del st.session_state[k]
            st.rerun()
    
    # Navigation
    nav_mode = st.segmented_control(
        "Navigation",
        options=["Data Quality", "Gait Analysis", "Fatigue Analysis"],
        selection_mode="single",
        default="Data Quality",
        label_visibility="collapsed"
    )
    st.markdown("---")

    # Content Area
    if nav_mode == "Data Quality":
        if 'raw_df' not in st.session_state:
            g_file = st.file_uploader("Upload Recording (.bin or .csv)", type=['bin', 'csv'])
            if g_file:
                with st.spinner("Ingesting and Validating Dataset..."):
                    meta, df = load_dataset(g_file)
                    st.session_state.raw_df = df
                    st.session_state.recording_meta = meta
                    st.session_state.validation_report, _ = logic.PipelineProcessor.validate(df)
                st.rerun()

        if 'raw_df' in st.session_state:
            # Inline Quality Controls
            with st.container(border=True):
                st.markdown("**DSP Pipeline Configuration**")
                c1, c2, c3 = st.columns([1.5, 1.5, 1])
                with c1:
                    tel = st.checkbox("Teleport Removal", True)
                    tel_th = st.number_input("Jump Threshold (m)", 0.1, 5.0, 0.5, disabled=not tel)
                with c2:
                    rep = st.checkbox("Interpolation", True)
                    sm = st.checkbox("Smoothing", True)
                    sm_w = st.number_input("Filter Window", 3, 101, 3, step=2, disabled=not sm)
                with c3:
                    st.markdown("&nbsp;")
                    if st.button("Apply Pipeline", type="primary", use_container_width=True):
                        df = st.session_state.raw_df.copy()
                        if tel: df, _ = logic.PipelineProcessor.remove_teleportation(df, float(tel_th))
                        if rep: df = logic.PipelineProcessor.repair(df)
                        if sm: df = logic.PipelineProcessor.smooth(df, int(sm_w))
                        st.session_state.clean_df = df
                        st.rerun()

                    if 'clean_df' in st.session_state:
                        st.info("Pipeline applied. Switch to **Gait Analysis** to view results.")

            st.subheader("Data Integrity Report")
            st.code(st.session_state.get('validation_report', "No data loaded."))
            
            j_col = st.selectbox("Inspect Node", logic.identify_joint_columns(st.session_state.raw_df.columns))
            with st.container(border=True):
                fig_q = go.Figure()
                fig_q.add_trace(go.Scatter(y=st.session_state.raw_df[j_col], name='Raw', line=dict(color=logic.COLOR_RAW_DATA, width=1, dash='dot')))
                if 'clean_df' in st.session_state:
                    fig_q.add_trace(go.Scatter(y=st.session_state.clean_df[j_col], name='Cleaned', line=dict(color=logic.COLOR_CLEAN_DATA, width=2.5)))
                st.plotly_chart(fig_q.update_layout(title=f"Quality Check: {j_col}", height=450, template="plotly_white"), use_container_width=True)

            # Export joint coordinates (cleaned if a pipeline has run, else raw)
            export_df = st.session_state.get('clean_df', st.session_state.raw_df)
            export_label = "Export Cleaned Joints CSV" if 'clean_df' in st.session_state else "Export Raw Joints CSV"
            st.download_button(
                export_label,
                export_df.to_csv(index=False).encode('utf-8'),
                "joints_cleaned.csv" if 'clean_df' in st.session_state else "joints_raw.csv",
                "text/csv",
                use_container_width=True,
            )

    elif nav_mode == "Gait Analysis":
        if 'raw_df' not in st.session_state:
            gait_file = st.file_uploader("Upload Recording (.bin or .csv)", type=['bin', 'csv'])
            if gait_file:
                with st.spinner("Analyzing Movement Patterns..."):
                    meta, df = load_dataset(gait_file)
                    st.session_state.raw_df = df
                    st.session_state.recording_meta = meta
                    st.session_state.validation_report, _ = logic.PipelineProcessor.validate(df)
                st.rerun()
        
        if 'raw_df' in st.session_state:
            df = st.session_state.get('clean_df', st.session_state.raw_df)
            ts_df, df_sec, df_min, stats_df, derived = process_analysis_data(df)

            # Inline Controls
            with st.container(border=True):
                st.markdown("**Visualization Settings**")
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    grp = st.selectbox("Temporal Grouping", ["Frames", "Seconds", "Minutes"], index=1)
                with c2:
                    env = st.checkbox("Show Envelopes", False)
                    trend = st.checkbox("Show Trends", True)
                with c3:
                    plot_df = {"Frames": ts_df.iloc[::max(1, len(ts_df)//1500)], "Seconds": df_sec, "Minutes": df_min}[grp]
                    csv_gait = plot_df.to_csv(index=False).encode('utf-8')
                    st.markdown("&nbsp;")
                    st.download_button(f"Export {grp} CSV", csv_gait, f"gait_metrics_{grp.lower()}.csv", "text/csv", use_container_width=True)

            # Recording Metadata Card
            if 'recording_meta' in st.session_state:
                m = st.session_state.recording_meta
                cam = m.get('camera', {})
                mp  = m.get('mediapipe', {})
                dur = ts_df['timestamp'].iloc[-1] - ts_df['timestamp'].iloc[0]
                with st.container(border=True):
                    st.markdown("**Recording Info**")
                    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
                    r1c1.metric("Date", m.get('date', '—'))
                    r1c2.metric("Duration", f"{int(dur // 60)}m {int(dur % 60)}s")
                    r1c3.metric("Frames", f"{len(ts_df):,}")
                    r1c4.metric("Camera FPS", cam.get('fps', '—'))

                    r2c1, r2c2, r2c3, r2c4 = st.columns(4)
                    r2c1.metric("Resolution", f"{cam.get('width','?')}×{cam.get('height','?')}")
                    r2c2.metric("Preset", cam.get('preset', '—'))
                    r2c3.metric("MP Complexity", mp.get('model_complexity', '—'))
                    r2c4.metric("MP Confidence", mp.get('min_confidence', '—'))

            # Key Gait Metrics (single-value, this iteration)
            def _fmt(v, suffix="", scale=1.0):
                return f"{v*scale:.1f}{suffix}" if v is not None and np.isfinite(v) else "—"

            vert_amp = stats_df.loc['vert_osc', 'rom'] if 'vert_osc' in stats_df.index else float('nan')
            with st.container(border=True):
                st.markdown("**Key Gait Metrics** — drift/oscillation normalized to torso length")
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Cadence", _fmt(derived['cadence'], " steps/min"))
                k2.metric("Step Frequency", _fmt(derived['step_hz'], " Hz"))
                k3.metric("X-Drift Rate", _fmt(derived['drift_rate'], " %torso/min", 100.0))
                k4.metric("Vertical Oscillation", _fmt(vert_amp, " %torso", 100.0),
                          help="Peak-to-peak vertical travel of the pelvis (% of torso length).")

            # Metrics Summary
            with st.container(border=True):
                sc1, sc2 = st.columns([0.7, 0.3], vertical_alignment="bottom")
                sc1.markdown("**Metrics Summary** — angles in °; `com_x`/`vert_osc` in torso lengths. `rom` = range of motion, `peak_vel` = peak rate (per s).")
                sc2.download_button(
                    "Export Summary CSV",
                    stats_df.to_csv().encode('utf-8'),
                    "metrics_summary.csv",
                    "text/csv",
                    use_container_width=True,
                )
                st.dataframe(
                    stats_df.style.format("{:.2f}", na_rep="—"),
                    use_container_width=True,
                    height=320,
                )

            x_col = {"Frames": "frame", "Seconds": "time_sec", "Minutes": "time_min"}[grp]

            # Trunk & head posture
            with st.container(border=True):
                st.plotly_chart(create_kinematic_plot(plot_df, x_col, ['trunk_lean', 'head_lean'], ["Trunk Lean", "Head Lean"], [logic.COLOR_LEFT, logic.COLOR_RIGHT], "Trunk & Head Lean (Sagittal)", env, trend), use_container_width=True)

            # Upper-limb swing (primary, well-tracked)
            arm_config = [
                ("Shoulder Swing", ['l_sho', 'r_sho'], ["Left Shoulder", "Right Shoulder"]),
                ("Elbow Flexion", ['l_elb', 'r_elb'], ["Left Elbow", "Right Elbow"]),
            ]
            arm_cols = st.columns(2)
            for i, (title, y_cols, names) in enumerate(arm_config):
                with arm_cols[i % 2]:
                    with st.container(border=True):
                        st.plotly_chart(create_kinematic_plot(plot_df, x_col, y_cols, names, [logic.COLOR_LEFT, logic.COLOR_RIGHT], title, env, trend), use_container_width=True)

            # Pelvis-derived signals
            pelvis_cols = st.columns(2)
            with pelvis_cols[0]:
                with st.container(border=True):
                    st.plotly_chart(create_kinematic_plot(plot_df, x_col, ['vert_osc'], ["Vertical"], [logic.COLOR_CENTER], "Pelvis Vertical Oscillation", env, trend, ylabel="Torso lengths"), use_container_width=True)
            with pelvis_cols[1]:
                with st.container(border=True):
                    st.plotly_chart(create_kinematic_plot(plot_df, x_col, ['com_x'], ["AP position"], [logic.COLOR_CENTER], "X-Drift (Anteroposterior Position)", env, trend, ylabel="Torso lengths"), use_container_width=True)

    elif nav_mode == "Fatigue Analysis":
        if 'raw_df' not in st.session_state:
            fat_file = st.file_uploader("Upload Recording (.bin or .csv)", type=['bin', 'csv'])
            if fat_file:
                with st.spinner("Analyzing Movement Patterns..."):
                    meta, df = load_dataset(fat_file)
                    st.session_state.raw_df = df
                    st.session_state.recording_meta = meta
                    st.session_state.validation_report, _ = logic.PipelineProcessor.validate(df)
                st.rerun()

        if 'raw_df' in st.session_state:
            df = st.session_state.get('clean_df', st.session_state.raw_df)
            ts_df, df_sec, df_min, stats_df, derived = process_analysis_data(df)
            duration = float(ts_df['timestamp'].iloc[-1] - ts_df['timestamp'].iloc[0])

            if duration < 60:
                st.warning("Recording is under a minute — baseline/fatigue analysis needs a longer session.")
            else:
                st.caption(
                    "**Fatigue = drift from a fresh baseline.** Pick a settled, "
                    "unfatigued window early in the run; the app then shows how far "
                    "your posture angles have moved from that baseline over time, in "
                    "degrees (e.g. *trunk lean +3° = leaning further forward as you tire*)."
                )

                # ---- Window controls (minute-based, treadmill-protocol friendly) ----
                duration_min = duration / 60.0
                with st.container(border=True):
                    st.markdown("**1. Trim the session**")
                    tc1, tc2, tc3 = st.columns([1, 1, 2])
                    with tc1:
                        warmup_min = st.number_input(
                            "Exclude warm-up (min)", 0.0, float(duration_min),
                            float(min(2.0, duration_min * 0.5)), step=0.5,
                            help="Treadmill adjustment period to drop from the start.",
                        )
                    with tc2:
                        cooldown_min = st.number_input(
                            "Exclude cool-down (min)", 0.0, float(duration_min),
                            0.0, step=0.5, help="Period to drop from the end.",
                        )
                    lo_bound = float(warmup_min)
                    hi_bound = float(duration_min - cooldown_min)
                    room = (hi_bound - lo_bound) >= 0.25
                    with tc3:
                        st.markdown("**2. Pick the unfatigued baseline**")
                        if room:
                            baseline_min = st.slider(
                                "Baseline window (min)", lo_bound, hi_bound,
                                (lo_bound, min(lo_bound + 2.0, hi_bound)), step=0.25,
                                help="A settled, unfatigued span used as the reference. "
                                     "Everything after it is compared against it.",
                            )
                        else:
                            baseline_min = (lo_bound, hi_bound)
                            st.info("Adjust trimming to leave room for a baseline.")

                    with st.expander("Advanced options"):
                        ac1, ac2 = st.columns([1, 1])
                        with ac1:
                            bin_label = st.selectbox("Comparison bin", ["1 min", "30 s", "2 min"], index=0)
                            value_label = st.radio(
                                "Deviation metric", ["Δ (degrees)", "% change"], horizontal=True,
                                help="Δ = bin-average minus your fresh baseline, in the metric's "
                                     "own units (degrees). Positive trunk-lean Δ means leaning "
                                     "further forward as you tire.",
                            )
                        with ac2:
                            metrics_sel = st.multiselect(
                                "Metrics to track", logic.ANGLE_METRICS,
                                default=logic.RELIABLE_FATIGUE_METRICS,
                                help="Trunk and head lean are the reliable sagittal-plane markers. "
                                     "Left/right shoulder & elbow angles are less trustworthy on a "
                                     "single side camera — the far limb is occluded and estimated.",
                            )
                        st.caption("Extra excluded regions in minutes (e.g. tracking glitches mid-run)")
                        custom_excl = st.data_editor(
                            pd.DataFrame({"Start (min)": pd.Series([], dtype=float),
                                          "End (min)": pd.Series([], dtype=float)}),
                            num_rows="dynamic", use_container_width=True,
                            hide_index=True, key="fatigue_excl",
                        )

                # ---- Assemble windows (seconds) ----
                exclude_regions = []
                if warmup_min > 0:
                    exclude_regions.append((0.0, warmup_min * 60.0))
                if cooldown_min > 0:
                    exclude_regions.append(((duration_min - cooldown_min) * 60.0, duration))
                for _, r in custom_excl.iterrows():
                    if pd.notna(r["Start (min)"]) and pd.notna(r["End (min)"]):
                        exclude_regions.append((float(r["Start (min)"]) * 60.0, float(r["End (min)"]) * 60.0))
                baseline_window = (baseline_min[0] * 60.0, baseline_min[1] * 60.0)
                bin_sec = {"1 min": 60.0, "30 s": 30.0, "2 min": 120.0}[bin_label]
                value_col = "delta" if value_label == "Δ (degrees)" else "pct_change"

                # ---- Compute baseline + fatigue curve ----
                # Require each bin to be at least half-full so a thin sliver at an
                # exclusion boundary or the session tail can't produce a wild Δ.
                fps = derived.get('fps', 30.0) or 30.0
                min_frames = max(1, int(0.5 * bin_sec * fps))
                ts_w = ts_df.assign(included=logic.build_time_mask(ts_df['timestamp'], exclude_regions))
                n_incl = int(ts_w['included'].sum())
                baseline = logic.compute_baseline(ts_w, baseline_window, metrics_sel)
                fatigue = logic.compute_fatigue_curve(ts_w, baseline, metrics_sel, bin_sec, min_frames)

                if not room:
                    st.error("Warm-up and cool-down leave no room for a baseline window. Reduce them.")
                elif not metrics_sel:
                    st.info("Select at least one metric to track (Advanced options).")
                elif baseline.empty or baseline['n'].fillna(0).max() == 0:
                    st.error("The baseline window contains no included data. Adjust the window or excluded regions.")
                else:
                    st.caption(
                        f"Included {n_incl:,} of {len(ts_w):,} frames · baseline "
                        f"{baseline_min[0]:.2f}–{baseline_min[1]:.2f} min "
                        f"(n={int(baseline['n'].max()):,} frames)"
                    )

                    # Baseline reference table
                    with st.container(border=True):
                        st.markdown("**Unfatigued Baseline** (reference)")
                        st.dataframe(
                            baseline.style.format({"baseline_mean": "{:.2f}", "baseline_std": "{:.2f}", "n": "{:.0f}"}, na_rep="—"),
                            use_container_width=True,
                        )

                    # Fatigue curve
                    with st.container(border=True):
                        ylabel = "Δ from baseline (°)" if value_col == "delta" else "% change from baseline"
                        st.plotly_chart(
                            create_fatigue_plot(fatigue, value_col, baseline_window, exclude_regions,
                                                title="Posture Drift From Baseline", ylabel=ylabel),
                            use_container_width=True,
                        )

                    # End-vs-baseline summary (last full bin per metric), in real units
                    last = fatigue.sort_values('time_min').groupby('metric').tail(1).set_index('metric')
                    summary = baseline.join(last[['mean', 'delta', 'pct_change']])
                    disp = summary.rename(columns={
                        'baseline_mean': 'Baseline (°)', 'baseline_std': 'Baseline SD',
                        'n': 'Baseline n', 'mean': 'End (°)', 'delta': 'Δ (°)', 'pct_change': 'Δ %',
                    })
                    with st.container(border=True):
                        sc1, sc2 = st.columns([0.7, 0.3], vertical_alignment="bottom")
                        sc1.markdown("**End vs Baseline** — your fresh baseline vs the final full bin, in degrees")
                        sc2.download_button(
                            "Export Fatigue CSV", fatigue.to_csv(index=False).encode('utf-8'),
                            "fatigue_curve.csv", "text/csv", use_container_width=True,
                        )
                        st.dataframe(
                            disp.style.format({
                                "Baseline (°)": "{:.1f}", "Baseline SD": "{:.1f}", "Baseline n": "{:.0f}",
                                "End (°)": "{:.1f}", "Δ (°)": "{:+.1f}", "Δ %": "{:+.1f}%",
                            }, na_rep="—"),
                            use_container_width=True,
                        )

if __name__ == "__main__":
    main()
