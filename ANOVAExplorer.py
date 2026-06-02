import io
import re
import zipfile

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from matplotlib import cm
from scipy.stats import f_oneway, sem


def significance_label(p_value: float) -> str:
    if p_value > 0.05:
        return "NS"
    if p_value > 0.009:
        return "*"
    if p_value > 0.0009:
        return "**"
    return "***"


def add_significance_bar(ax, x1, x2, y, height, text):
    ax.plot([x1, x1, x2, x2], [y, y + height, y + height, y], lw=1.5, c="black")
    ax.text((x1 + x2) / 2, y + height, text, ha="center", va="bottom", fontsize=12)


def safe_filename(value: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_.-]", "_", str(value))
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "parameter"


def run_anova(df: pd.DataFrame, exp_group: list[str], ctrl_group: list[str]):
    palette = list(cm.tab10.colors) + list(cm.Set2.colors) + list(cm.Paired.colors)
    control_colors = {ctrl: palette[i % len(palette)] for i, ctrl in enumerate(ctrl_group)}
    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()

    results = []
    plot_bytes = {}

    for param in numeric_cols:
        fig, ax = plt.subplots(figsize=(8, 6))

        plot_labels = []
        plot_means = []
        plot_errors = []

        for genotype in exp_group + ctrl_group:
            vals = df[df["Genotype"] == genotype][param].dropna()
            if len(vals) == 0:
                continue
            plot_labels.append(genotype)
            plot_means.append(vals.mean())
            plot_errors.append(sem(vals))

        if not plot_means:
            plt.close(fig)
            continue

        bar_colors = []
        for genotype in plot_labels:
            if genotype in exp_group:
                bar_colors.append("lightgray")
            else:
                bar_colors.append(control_colors[genotype])

        ax.bar(
            plot_labels,
            plot_means,
            yerr=plot_errors,
            capsize=5,
            color=bar_colors,
            edgecolor="black",
            linewidth=1.2,
        )

        for i, genotype in enumerate(plot_labels):
            vals = df[df["Genotype"] == genotype][param].dropna()
            x = np.random.normal(loc=i, scale=0.04, size=len(vals))
            ax.scatter(x, vals, color="black", s=25, zorder=10)

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

                _, p_value = f_oneway(exp_vals, ctrl_vals)
                sig = significance_label(p_value)
                results.append(
                    {
                        "Parameter": param,
                        "Experimental": exp,
                        "Control": ctrl,
                        "P_value": p_value,
                        "Significance": sig,
                    }
                )

                exp_idx = plot_labels.index(exp)
                ctrl_idx = plot_labels.index(ctrl)
                y = ymax * (1.10 + sig_level * 0.08)
                add_significance_bar(ax, exp_idx, ctrl_idx, y, ymax * 0.03, sig)
                sig_level += 1

        ax.set_ylim(top=ymax * (1.25 + sig_level * 0.08))
        ax.set_title(param)
        ax.set_ylabel(param)
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()

        image_buffer = io.BytesIO()
        fig.savefig(image_buffer, format="png", dpi=300)
        image_buffer.seek(0)
        plot_bytes[safe_filename(param)] = image_buffer.getvalue()
        plt.close(fig)

    results_df = pd.DataFrame(results)
    return results_df, plot_bytes


def build_zip_bytes(results_df: pd.DataFrame, plot_bytes: dict[str, bytes]) -> bytes:
    output_zip = io.BytesIO()
    with zipfile.ZipFile(output_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
            results_df.to_excel(writer, index=False, sheet_name="anova_results")
        excel_buffer.seek(0)
        zip_file.writestr("anova_results.xlsx", excel_buffer.getvalue())

        for param_name, img_bytes in plot_bytes.items():
            zip_file.writestr(f"{param_name}.png", img_bytes)

    output_zip.seek(0)
    return output_zip.getvalue()


def main():
    st.set_page_config(page_title="ANOVA Explorer", layout="wide")
    st.title("ANOVA Explorer")
    st.write("Upload an Excel file, select groups, and run one-way ANOVA plots.")

    uploaded_file = st.file_uploader("Upload Excel file (.xlsx)", type=["xlsx"])
    if uploaded_file is None:
        st.info("Upload an Excel file to begin.")
        return

    try:
        df = pd.read_excel(uploaded_file)
    except Exception as exc:
        st.error(f"Could not read Excel file: {exc}")
        return

    if "Genotype" not in df.columns:
        st.error("Column 'Genotype' not found in the uploaded file.")
        return

    genotypes = sorted(df["Genotype"].dropna().unique().tolist())
    if not genotypes:
        st.error("No genotype values found in the 'Genotype' column.")
        return

    st.subheader("Group Selection")
    col1, col2 = st.columns(2)

    with col1:
        exp_group = st.multiselect(
            "Experimental Group",
            options=genotypes,
            default=[],
        )

    with col2:
        ctrl_group = st.multiselect(
            "Control Group",
            options=[g for g in genotypes if g not in exp_group],
            default=[],
        )

    st.caption("A genotype can belong to one group at a time.")

    if st.button("Run ANOVA", type="primary"):
        if not exp_group:
            st.error("Select at least one experimental genotype.")
            return
        if not ctrl_group:
            st.error("Select at least one control genotype.")
            return

        with st.spinner("Running ANOVA and generating plots..."):
            results_df, plots = run_anova(df, exp_group, ctrl_group)

        if results_df.empty and not plots:
            st.warning("No valid numeric parameters were found for ANOVA.")
            return

        st.success("ANOVA complete.")
        st.subheader("Results")
        st.dataframe(results_df, use_container_width=True)

        zip_bytes = build_zip_bytes(results_df, plots)
        st.download_button(
            label="Download all results (.zip)",
            data=zip_bytes,
            file_name="anova_results.zip",
            mime="application/zip",
        )

        st.subheader("Generated Plots")
        for param_name, image_data in plots.items():
            st.image(image_data, caption=param_name, use_container_width=True)


if __name__ == "__main__":
    main()
