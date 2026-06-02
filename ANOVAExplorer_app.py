import streamlit as st
import pandas as pd
import numpy as np
import os
import re
import matplotlib.pyplot as plt
import zipfile
from io import BytesIO

from scipy.stats import f_oneway, sem
from matplotlib import cm

st.set_page_config(page_title="ANOVA Explorer", layout="wide")

st.title("🧬 ANOVA Explorer (Genotype Analysis Tool)")


# ---------------- Helper functions ----------------
def significance_label(p):
    if p > 0.05:
        return "NS"
    elif p > 0.009:
        return "*"
    elif p > 0.0009:
        return "**"
    else:
        return "***"


def add_significance_bar(ax, x1, x2, y, h, text):
    ax.plot([x1, x1, x2, x2],
            [y, y + h, y + h, y],
            lw=1.5,
            c="black")

    ax.text((x1 + x2) / 2,
            y + h,
            text,
            ha="center",
            va="bottom",
            fontsize=12)


# ---------------- Upload file ----------------
uploaded_file = st.file_uploader("📂 Upload Excel File", type=["xlsx"])

if uploaded_file:

    df = pd.read_excel(uploaded_file)

    if "Genotype" not in df.columns:
        st.error("Column 'Genotype' not found in file.")
        st.stop()

    genotypes = sorted(df["Genotype"].dropna().unique().tolist())

    # ---------------- Selection ----------------
    col1, col2 = st.columns(2)

    with col1:
        exp_group = st.multiselect("🧪 Experimental Group", genotypes)

    with col2:
        ctrl_group = st.multiselect("⚖️ Control Group", genotypes)

    # prevent overlap
    overlap = set(exp_group).intersection(ctrl_group)
    if overlap:
        st.error(f"Overlap detected: {', '.join(overlap)}")
        st.stop()

    # ---------------- Output folder ----------------
    folder_name = st.text_input("📁 Results Folder Name", "anova_results")

    run = st.button("🚀 Run ANOVA")

    # ---------------- Run analysis ----------------
    if run:

        if len(exp_group) == 0 or len(ctrl_group) == 0:
            st.error("Select both experimental and control groups.")
            st.stop()

        output_dir = os.path.join(os.getcwd(), folder_name)
        os.makedirs(output_dir, exist_ok=True)

        numeric_cols = df.select_dtypes(include=np.number).columns.tolist()

        results = []

        # color map for controls
        control_colors = {}
        palette = list(cm.tab10.colors) + list(cm.Set2.colors)

        for i, ctrl in enumerate(ctrl_group):
            control_colors[ctrl] = palette[i % len(palette)]

        for param in numeric_cols:

            fig, ax = plt.subplots(figsize=(8, 6))

            plot_labels = []
            plot_means = []
            plot_sem = []

            # ---------------- summary stats ----------------
            for g in exp_group + ctrl_group:

                vals = df[df["Genotype"] == g][param].dropna()

                if len(vals) == 0:
                    continue

                plot_labels.append(g)
                plot_means.append(vals.mean())
                plot_sem.append(sem(vals))

            if len(plot_means) == 0:
                continue

            # ---------------- bar colors ----------------
            bar_colors = []
            for g in plot_labels:
                if g in exp_group:
                    bar_colors.append("lightgray")
                else:
                    bar_colors.append(control_colors[g])

            ax.bar(plot_labels,
                   plot_means,
                   yerr=plot_sem,
                   capsize=5,
                   color=bar_colors,
                   edgecolor="black",
                   linewidth=1.2)

            # ---------------- scatter individual points ----------------
            for i, g in enumerate(plot_labels):

                vals = df[df["Genotype"] == g][param].dropna()

                x = np.random.normal(i, 0.05, size=len(vals))

                ax.scatter(x,
                           vals,
                           color="black",
                           s=25,
                           alpha=0.7,
                           zorder=10)

            # ---------------- stats ----------------
            ymax = max(plot_means)
            sig_level = 0

            for exp in exp_group:

                exp_vals = df[df["Genotype"] == exp][param].dropna()

                if len(exp_vals) < 2:
                    continue

                for ctrl in ctrl_group:

                    ctrl_vals = df[df["Genotype"] == ctrl][param].dropna()

                    if len(ctrl_vals) < 2:
                        continue

                    stat, p = f_oneway(exp_vals, ctrl_vals)

                    sig = significance_label(p)

                    results.append({
                        "Parameter": param,
                        "Experimental": exp,
                        "Control": ctrl,
                        "P_value": p,
                        "Significance": sig
                    })

                    x1 = plot_labels.index(exp)
                    x2 = plot_labels.index(ctrl)

                    y = ymax * (1.10 + sig_level * 0.08)

                    add_significance_bar(ax, x1, x2, y, ymax * 0.03, sig)

                    sig_level += 1

            ax.set_title(param)
            ax.set_ylabel(param)
            ax.set_xticklabels(plot_labels, rotation=45, ha="right")

            plt.tight_layout()

            # ---------------- safe filename ----------------
            safe_name = re.sub(r'[^A-Za-z0-9_.-]', '_', str(param))
            safe_name = re.sub(r'_+', '_', safe_name).strip('_')

            # save figure
            fig_path = os.path.join(output_dir, f"{safe_name}.png")
            fig.savefig(fig_path, dpi=300)

            st.pyplot(fig)

            zip_buffer = BytesIO()

            with zipfile.ZipFile(zip_buffer, "w") as zipf:

                for file in os.listdir(output_dir):
                    if file.endswith(".png"):
                        zipf.write(
                            os.path.join(output_dir, file),
                            arcname=file
                        )

            zip_buffer.seek(0)

            st.download_button(
                label="📦 Download All Figures (ZIP)",
                data=zip_buffer,
                file_name="anova_figures.zip",
                mime="application/zip"
            )

        # ---------------- save results ----------------
        results_df = pd.DataFrame(results)

        excel_path = os.path.join(output_dir, "anova_results.xlsx")
        results_df.to_excel(excel_path, index=False)

        st.success(f"Results saved in: {output_dir}")

        with open(excel_path, "rb") as f:
            st.download_button(
                "📥 Download ANOVA Results",
                f,
                file_name="anova_results.xlsx"
            )