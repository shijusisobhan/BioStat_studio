import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re
from io import BytesIO
from pathlib import Path
import zipfile

from scipy.stats import f_oneway, sem
from matplotlib import cm

st.set_page_config(page_title="ANOVA Explorer", layout="wide")

st.title("🧬 ANOVA Explorer (Publication-Ready Stats Tool)")


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


def safe_filename(name):
    safe = re.sub(r'[^A-Za-z0-9_.-]', '_', str(name))
    return re.sub(r'_+', '_', safe).strip('_')


def safe_subfolder_name(name):
    """Allow only a single folder segment (no path separators)."""
    cleaned = re.sub(r'[<>:"/\\|?*]', '_', str(name).strip())
    cleaned = cleaned.strip('. ')
    return cleaned or "anova_results"


def save_results_to_folder(output_dir, all_figures, results_df):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for fname, fbytes in all_figures.items():
        (output_dir / fname).write_bytes(fbytes)

    excel_path = output_dir / "anova_results.xlsx"
    results_df.to_excel(excel_path, index=False, engine="openpyxl")

    zip_path = output_dir / "anova_figures.zip"
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for fname, fbytes in all_figures.items():
            zipf.writestr(fname, fbytes)

    return output_dir, excel_path, zip_path


# ---------------- Data source ----------------
st.subheader("📂 Data source")
data_folder = st.text_input(
    "Folder containing Excel files",
    help="Local path where your .xlsx files live. Results are saved in a subfolder here.",
)

selected_xlsx = None
data_path = None

if data_folder.strip():
    data_path = Path(data_folder.strip()).expanduser().resolve()
    if not data_path.is_dir():
        st.error(f"Folder not found: {data_path}")
        st.stop()

    xlsx_files = sorted(data_path.glob("*.xlsx"))
    if not xlsx_files:
        st.warning(f"No .xlsx files found in {data_path}")
        st.stop()

    selected_name = st.selectbox(
        "Select Excel file",
        [f.name for f in xlsx_files],
    )
    selected_xlsx = data_path / selected_name
else:
    uploaded_file = st.file_uploader(
        "Or upload an Excel file (browser upload — save folder must be set manually below)",
        type=["xlsx"],
    )
    if uploaded_file:
        selected_xlsx = uploaded_file

results_subfolder = st.text_input(
    "Results subfolder name",
    value="anova_results",
    help="Created inside the Excel folder. All figures and tables are saved here automatically.",
)

if selected_xlsx is None:
    st.info("Enter a data folder and pick a file, or upload an Excel file to begin.")
    st.stop()

# Resolve parent folder for output (upload mode uses optional save path)
if isinstance(selected_xlsx, Path):
    excel_parent = selected_xlsx.parent
    df = pd.read_excel(selected_xlsx)
    source_label = str(selected_xlsx)
else:
    save_parent = st.text_input(
        "Save results in this folder (required for upload mode)",
        help="Same idea as the data folder above — a subfolder with your chosen name will be created here.",
    )
    if not save_parent.strip():
        st.warning("Set a save folder, or use the folder browser above so results can be saved automatically.")
        st.stop()
    excel_parent = Path(save_parent.strip()).expanduser().resolve()
    if not excel_parent.is_dir():
        st.error(f"Save folder not found: {excel_parent}")
        st.stop()
    df = pd.read_excel(selected_xlsx)
    source_label = uploaded_file.name

output_dir = excel_parent / safe_subfolder_name(results_subfolder)
st.caption(f"Results will be saved to: `{output_dir}`")

if "Genotype" not in df.columns:
    st.error("Missing 'Genotype' column.")
    st.stop()

genotypes = sorted(df["Genotype"].dropna().unique().tolist())

# ---------------- Selection ----------------
col1, col2 = st.columns(2)

with col1:
    exp_group = st.multiselect("🧪 Experimental Group", genotypes)

with col2:
    ctrl_group = st.multiselect("⚖️ Control Group", genotypes)

overlap = set(exp_group).intersection(ctrl_group)

if overlap:
    st.error(f"Overlap detected: {', '.join(overlap)}")
    st.stop()

run = st.button("🚀 Run ANOVA")

# ---------------- Run ----------------
if run:

    if len(exp_group) == 0 or len(ctrl_group) == 0:
        st.error("Select both groups.")
        st.stop()

    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()

    results = []
    all_figures = {}

    # color mapping
    control_colors = {}
    palette = list(cm.tab10.colors) + list(cm.Set2.colors)

    for i, ctrl in enumerate(ctrl_group):
        control_colors[ctrl] = palette[i % len(palette)]

    # ---------------- LOOP PARAMETERS ----------------
    for param in numeric_cols:

        fig, ax = plt.subplots(figsize=(8, 6))

        plot_labels = []
        plot_means = []
        plot_sem = []

        # summary stats
        for g in exp_group + ctrl_group:

            vals = df[df["Genotype"] == g][param].dropna()

            if len(vals) == 0:
                continue

            plot_labels.append(g)
            plot_means.append(vals.mean())
            plot_sem.append(sem(vals))

        if len(plot_means) == 0:
            plt.close(fig)
            continue

        # colors
        bar_colors = [
            "lightgray" if g in exp_group else control_colors[g]
            for g in plot_labels
        ]

        ax.bar(plot_labels,
               plot_means,
               yerr=plot_sem,
               capsize=5,
               color=bar_colors,
               edgecolor="black",
               linewidth=1.2)

        # individual points
        for i, g in enumerate(plot_labels):

            vals = df[df["Genotype"] == g][param].dropna()

            x = np.random.normal(i, 0.05, size=len(vals))

            ax.scatter(x,
                       vals,
                       color="black",
                       s=25,
                       alpha=0.7,
                       zorder=10)

        # stats
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

        safe_name = safe_filename(param)

        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=300, bbox_inches="tight")
        buf.seek(0)

        st.pyplot(fig)
        plt.close(fig)

        all_figures[f"{safe_name}.png"] = buf.getvalue()

    # ---------------- RESULTS EXCEL ----------------
    results_df = pd.DataFrame(results)

    saved_dir, excel_path, zip_path = save_results_to_folder(
        output_dir, all_figures, results_df
    )

    st.success(f"Analysis complete. Results saved to `{saved_dir}`")
    st.markdown(
        f"- **Source:** `{source_label}`  \n"
        f"- **Excel:** `{excel_path.name}`  \n"
        f"- **Figures:** {len(all_figures)} PNG file(s)  \n"
        f"- **ZIP:** `{zip_path.name}`"
    )

    # Optional browser downloads (same files already on disk)
    excel_buffer = BytesIO()
    results_df.to_excel(excel_buffer, index=False, engine="openpyxl")
    excel_buffer.seek(0)

    st.download_button(
        label="📊 Download ANOVA Results (Excel)",
        data=excel_buffer,
        file_name="anova_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for fname, fbytes in all_figures.items():
            zipf.writestr(fname, fbytes)
    zip_buffer.seek(0)

    st.download_button(
        label="📦 Download All Figures (ZIP)",
        data=zip_buffer,
        file_name="anova_figures.zip",
        mime="application/zip",
    )
