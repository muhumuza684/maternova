Measuring Internal Product Attributes: Software Size
1. Introduction
Software size is an internal product attribute that describes a software system based on its structure without executing it. It is an important metric used to estimate:
•	Development effort 
•	Cost 
•	Productivity 
In this implementation, software size is measured using length-based metrics, specifically:
•	Lines of Code (LOC) 
•	Halstead Metrics 
2. Objectives
The objectives of this implementation are to:
•	Measure the physical size of the system (app.py) 
•	Analyze the internal structure of the code 
•	Provide quantitative metrics for evaluating software complexity and maintainability 
3. Metrics Implemented
3.1 Lines of Code (LOC)
LOC measures the physical size of the software system.
Metrics Computed:
•	Total LOC → Total number of lines in the file 
•	Blank Lines → Empty lines 
•	Comment Lines (CLOC) → Lines containing comments 
•	Effective LOC (NCLOC) → Executable lines 
•	Comment Density → Ratio of comment lines to total lines 
Formula:
LOC = NCLOC + CLOC
Comment Density:
Comment Density = CLOC / LOC
Implementation:
•	The file is read line by line 
•	Blank lines are identified using:
line.strip() == ""
•	Comment lines are detected by checking for the presence of # in each line 
•	Effective LOC is computed by excluding blank and comment lines 
•	Comment density is calculated as the ratio of comment lines to total lines 
Improvements Made:
•	Inline comments are now detected (e.g., x = 5 # comment) 
•	Comment density was added to provide insight into documentation quality 
Significance:
•	Simple and easy to compute 
•	Correlates with development effort 
•	Comment density helps evaluate code documentation 
Limitations:
•	Depends on coding style 
•	May slightly overestimate comments if # appears inside strings 
•	Does not reflect functionality 
3.2 Halstead Metrics
Halstead metrics measure software size based on operators and operands.
Definitions:
•	μ₁ → Number of distinct operators 
•	μ₂ → Number of distinct operands 
•	N₁ → Total occurrences of operators 
•	N₂ → Total occurrences of operands 
Derived Metrics:
Program Vocabulary (μ):
μ = μ₁ + μ₂
Program Length (N):
N = N₁ + N₂
Implementation:
•	Python’s tokenize module is used for lexical analysis 
•	Operators are identified using token type OP 
•	Operands include: 
o	Variable names 
o	Numbers 
o	Strings 
•	Sets are used to count distinct elements 
•	Counters track total occurrences 
Improvements Made:
•	Error handling was added using try-except to prevent crashes during tokenization 
•	This ensures the analyzer works reliably even if the code contains unexpected formatting 
Significance:
•	Measures code complexity 
•	Reflects mental effort required to write the program 
•	Useful for estimating maintainability 
Limitations:
•	Language dependent 
•	Token classification may vary 
4. Tools Used
•	Python 
•	Built-in modules: 
o	tokenize (for lexical analysis) 
o	re (for pattern matching) 
o	io (for reading code as a stream) 
5. Results
Example output from analyzing app.py:
LOC Metrics:
Total LOC: 2967
Blank Lines: 176
Comment Lines: 191
Effective LOC: 2600
Comment Density: 0.06

Halstead Metrics:
Distinct Operators (μ1): 17
Distinct Operands (μ2): 341
Program Vocabulary (μ): 358
Program Length (N): 3638

6. Discussion
The LOC metric provides a simple and direct measurement of software size, while Halstead metrics provide deeper insight into code complexity.
The addition of comment density enhances the analysis by evaluating the level of code documentation.
Together, these metrics provide a more comprehensive understanding of:
•	Code size 
•	Code complexity 
•	Maintainability 
•	Documentation quality 
7. Conclusion
The implementation successfully demonstrates how internal product attributes can be measured using automated tools. By combining LOC and Halstead metrics, along with improvements such as comment density and error handling, the system provides a reliable and meaningful analysis of software size.
8. Future Improvements
•	Implement Cyclomatic Complexity 
•	Improve comment detection using advanced parsing 
•	Analyze multiple files instead of a single file 
•	Integrate metrics into the Flask dashboard 
•	Visualize results using graphs

---

## Part 2: Software Cost Estimation Metrics

### 1. Introduction

Software cost estimation is the process of predicting the effort, time, and resources required to develop a software system. This section applies classical and contemporary estimation models from Chapter 7 of the SENG 421 course to **Maternova** — a Flask-based maternal health management web application (`app.py`, ~2,780 effective SLOC).

Models applied:

- **Basic COCOMO** (Boehm, 1981)
- **Intermediate COCOMO** (with 15 cost drivers and EAF)
- **COCOMO II Early Design** (Function Point based)
- **COCOMO II Post-Architecture** (with scale factors and 17 cost drivers)
- **Rayleigh-Putnam SLIM** model (schedule vs effort tradeoff)
- **Case-Based Reasoning (CBR)** (analogy-based estimation)

---

### 2. System Classification

| Attribute | Value |
|---|---|
| System | Maternova – Maternal Health Web App |
| Language | Python / Flask / SQLAlchemy |
| Total LOC | 2,967 |
| Effective SLOC (NCLOC) | 2,780 |
| KLOC | 2.780 |
| COCOMO Mode | Semi-Detached |
| Developer Profile | Solo developer, early professional |

**Justification for Semi-Detached mode:** Maternova is built by a solo developer with moderate Flask experience but limited medical-domain background. It is neither a simple well-understood app (Organic) nor a real-time safety-critical system (Embedded).

---

### 3. Basic COCOMO (Boehm, 1981)

**Formula:**
```
E = a × (KLOC)^b        [Person-Months]
T = c × (E)^d           [Development Months]
```

**Model coefficients:**

| Mode | a | b | c | d |
|---|---|---|---|---|
| Organic | 2.4 | 1.05 | 2.5 | 0.38 |
| Semi-Detached | 3.0 | 1.12 | 2.5 | 0.35 |
| Embedded | 3.6 | 1.20 | 2.5 | 0.32 |

**Results for Maternova (KLOC = 2.780):**

| Mode | Effort (PM) | Tdev (months) | Avg Team |
|---|---|---|---|
| Organic | 7.02 | 5.24 | 1.34 |
| **Semi-Detached** ★ | **9.43** | **5.48** | **1.72** |
| Embedded | 12.28 | 5.58 | 2.20 |

---

### 4. Intermediate COCOMO (with EAF)

Extends Basic COCOMO with an **Effort Adjustment Factor (EAF)** derived from 15 cost drivers.

```
E = a × (KLOC)^b × EAF
EAF = product of all effort multipliers (EM)
```

**Cost Driver Ratings for Maternova:**

| Driver | Rating | EM | Justification |
|---|---|---|---|
| RELY | High | 1.15 | Medical patient data — high failure cost |
| DATA | Low | 0.94 | SQLite, modest data volume |
| CPLX | Nominal | 1.00 | Standard CRUD + analytics |
| TIME | Nominal | 1.00 | No real-time constraints |
| STOR | Nominal | 1.00 | Lightweight SQLite |
| VIRT | Low | 0.87 | Stable Python/Flask platform |
| TURN | Low | 0.87 | Fast local dev turnaround |
| ACAP | Nominal | 1.00 | Competent developer |
| AEXP | Low | 1.13 | Limited medical-domain experience |
| PCAP | Nominal | 1.00 | Solid Python capability |
| VEXP | High | 0.90 | Good Flask/SQLAlchemy familiarity |
| LEXP | High | 0.95 | Strong Python experience |
| MODP | High | 0.91 | Uses ORM, blueprints, hashing |
| TOOL | High | 0.91 | VS Code, Git, Netlify, Flask CLI |
| SCED | Nominal | 1.00 | No schedule compression |

**EAF = 0.6546**

**Result:**

| Metric | Value |
|---|---|
| Effort | 6.17 PM |
| Tdev | 4.73 months |
| Avg Team | 1.31 persons |

*The EAF < 1.0 indicates that strong tooling and platform experience reduce the expected effort.*

---

### 5. COCOMO II – Early Design Model

Uses **Function Points (FP)** as the size measure before detailed design is available.

**Function Point Count for Maternova:**

| Type | Description | Count | Weight | Points |
|---|---|---|---|---|
| EI | External Inputs (forms) | 8 | 4 | 32 |
| EO | External Outputs (views) | 6 | 5 | 30 |
| EQ | External Inquiries (queries) | 5 | 4 | 20 |
| ILF | Internal Logical Files (DB models) | 6 | 10 | 60 |
| EIF | External Interface Files | 0 | 7 | 0 |
| | **Total UFC** | | | **142** |

**Derivation:**
```
Derived KLOC = UFC × LOC/FP = 142 × 50 = 7,100 SLOC = 7.1 KLOC
EAF (7 combined drivers) = 1.0804
E = 2.45 × 7.1 × 1.0804 = 18.79 PM
```

*Note: The FP-derived KLOC (7.1) is higher than measured KLOC (2.78) because the Python average of 50 SLOC/FP reflects typical industry projects; Maternova's dense Flask routes compress LOC.*

---

### 6. COCOMO II – Post-Architecture Model

Most accurate COCOMO II variant — applied after architecture is established.

**Formula:**
```
E = 2.45 × (KLOC)^b × EAF
b = 0.91 + 0.01 × Σ(SF_i)
```

**Scale Factors:**

| SF | Rating | Value | Justification |
|---|---|---|---|
| PREC | Nominal | 3.72 | Partially new domain |
| FLEX | High | 2.03 | Flexible requirements during build |
| RESL | Low | 5.65 | Limited upfront architecture |
| TEAM | VeryHigh | 1.10 | Solo — no coordination overhead |
| PMAT | Low | 6.24 | Early-stage, CMM Level ~1–2 |
| **Σ** | | **18.74** | |

```
b = 0.91 + 0.01 × 18.74 = 1.0974
EAF (17 drivers) = 0.6567
E = 2.45 × (2.780)^1.0974 × 0.6567 = 4.94 PM
```

---

### 7. Rayleigh-Putnam SLIM Model

Models the distribution of effort over time using the Rayleigh curve.

**Software Equation:**
```
size = C × B^(1/3) × T^(4/3)
Solving for effort: B = (size / C)^3 / T^4
Peak effort: E_peak = 0.3945 × B
```

**Parameters for Maternova:**

| Parameter | Value | Description |
|---|---|---|
| size | 2,780 SLOC | Effective LOC |
| PI | 13 | Systems software |
| C | 13,530 | Productivity constant |
| D | 15 | Standalone system |

**Schedule vs. Effort Tradeoff:**

| T (years) | B (staff-years) | E_peak (years) |
|---|---|---|
| 1.0 | 0.0090 | 0.0030 |
| 1.5 | 0.0020 | 0.0010 |
| 2.0 | 0.0010 | 0.0000 |

**Key finding — Schedule Compression Penalty:**
```
Halving T from 2.0 → 1.0 years multiplies effort by ~16×
(Because B ∝ T^-4: 1 / 0.5^4 = 16)
```

---

### 8. Case-Based Reasoning (CBR)

Predicts effort by adapting estimates from similar historical projects.

**Adaptation formula:**
```
Adapted_Effort = (New_Size / Retrieved_Size) × Retrieved_Effort
```

**Case Table:**

| Attribute | Maternova (New) | PatientTrack Pro | ClinicManager |
|---|---|---|---|
| Category | Medical Web App | Medical Web App | Healthcare Scheduler |
| Language | Python/Flask | Python/Flask | Python/Django |
| Team Size | 1 | 2 | 2 |
| Size (KLOC) | 2.78 | 4.5 | 3.8 |
| Known Effort | ? | 18.0 PM | 15.0 PM |
| Similarity | — | 88% | 61% |

**Predictions:**

| Strategy | Effort |
|---|---|
| Strategy 1: Closest project only | 11.12 PM |
| Strategy 2: Simple average | 11.05 PM |
| Strategy 3: Weighted by similarity ★ | **11.06 PM** |

---

### 9. Summary – Effort Estimates Comparison

| Model | Effort (PM) |
|---|---|
| COCOMO Basic (Semi-Detached) | 9.43 |
| COCOMO Intermediate (with EAF) | 6.17 |
| COCOMO II Early Design | 18.79 |
| COCOMO II Post-Architecture | 4.94 |
| CBR Weighted Average | 11.06 |

**Interpretation:** The estimates range from ~5 to ~19 PM. The Post-Architecture model (4.94 PM) gives the most precise result since it uses actual measured KLOC and project-specific scale factors. The Early Design model (18.79 PM) is higher because it uses FP-derived KLOC, which overestimates size for dense Python code. The CBR estimate (11.06 PM) reflects real-world analogies and is a reasonable cross-check.

---

### 10. Implementation

All cost models are implemented in `cost_metrics.py`. Run with:

```bash
python3 cost_metrics.py
```

---

### 11. Conclusion

This implementation demonstrates how software cost estimation models from SENG 421 Chapter 7 can be applied systematically to a real-world system. By combining algorithmic models (COCOMO, SLIM) with analogy-based reasoning (CBR), the analysis provides a multi-perspective view of the effort required to build Maternova. The range of 5–19 PM across models is consistent with the inherent uncertainty in early-stage software estimation.

---

### 12. Future Improvements

- Implement COCOMO II with extended ISBSG calibration data
- Build a web dashboard (Flask route) to visualize estimates interactively
- Add Monte Carlo simulation for effort range/confidence intervals
- Apply metrics to additional modules as the system grows
