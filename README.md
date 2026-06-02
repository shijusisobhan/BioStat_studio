
# 🧬 ANOVA Explorer – Genotype Analysis & Visualization Tool

A **Streamlit-based interactive bioinformatics tool** for performing statistical comparison of experimental and control genotypes across multiple quantitative parameters.

This app generates **publication-ready figures** and performs **one-way ANOVA comparisons** between user-defined groups.

---

# 🚀 Live App

Once deployed on Streamlit Cloud:

👉 [https://your-app-name.streamlit.app](https://anovaexplorer.streamlit.app/)

---

# 📊 What this app does

This tool allows researchers to:

### ✔ Upload Excel dataset
- Requires a column named: `Genotype`
- Other columns should be numeric parameters (e.g., gene expression, behavioral metrics, physiological values)

---

### ✔ Select groups interactively
- Choose **Experimental genotypes**
- Choose **Control genotypes**
- Prevents overlap automatically

---

### ✔ Perform statistical analysis
For each numeric parameter:

- Computes **mean ± SEM**
- Performs **one-way ANOVA (Experimental vs Control comparisons)**
- Calculates **p-values**
- Assigns significance levels:

| p-value range | Label |
|--------------|------|
| p > 0.05 | NS |
| p ≤ 0.05 | * |
| p ≤ 0.009 | ** |
| p ≤ 0.0009 | *** |

---

### ✔ Generate publication-quality plots
Each parameter generates a figure with:

- 📊 Bar plot (mean values)
- 📏 Error bars (SEM)
- ⚫ Individual data points (jittered scatter)
- ⚖️ Significance brackets between groups
- 🎨 Consistent color scheme:
  - Experimental = light gray
  - Control = distinct colors per genotype

---

### ✔ Export results
Users can download:

- 📊 ANOVA results (Excel file)
- 🖼 Individual plots (PNG)
- 📦 All plots bundled as ZIP file

---

# 📁 Input format

Upload an Excel file (`.xlsx`) with structure like:

| Genotype | Parameter1 | Parameter2 | Parameter3 |
|----------|------------|------------|------------|
| WT       | 1.2        | 3.4        | 5.6        |
| Mut1     | 1.5        | 3.1        | 6.0        |

### Requirements:
- Must contain a column named: `Genotype`
- Remaining columns should be numeric measurements

---

# 📈 Output generated

For each parameter:

### 1. Figure
- Mean ± SEM barplot
- Individual data points
- Significance annotations

### 2. Statistical table
| Parameter | Experimental | Control | P-value | Significance |

### 3. Download options
- PNG per figure
- ZIP file of all figures
- Excel summary file

---

# 🧪 Statistical method

- One-way ANOVA using `scipy.stats.f_oneway`
- Pairwise comparisons:
  - Each experimental genotype vs each control genotype
- No assumption of equal group sizes required

---

# 🖥️ How to run locally

## 1. Clone repository
```bash
git clone https://github.com/your-username/anova-explorer.git
cd anova-explorer
