"""
empirical_investigation.py
==========================
Empirical Software Engineering Investigation
Based on SENG 421 – Chapter 4: Empirical Investigation

This module implements the full SE investigation framework:
  1. Experimental Context  – hypothesis definition
  2. Experimental Design   – variable identification & control
  3. Data Collection       – metric extraction from source code
  4. Analysis              – statistical analysis of collected data
  5. Presentation          – structured result output
  6. Interpretation        – conclusions, limitations, significance

Target file: app.py (Maternova Flask application)
"""

import re
import math
import tokenize
import ast
from io import BytesIO
from dataclasses import dataclass, field
from typing import Dict, List, Any


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 1 – EXPERIMENTAL CONTEXT
# ──────────────────────────────────────────────────────────────────────────────

EXPERIMENT_CONTEXT = {
    "title": "Empirical Investigation of Software Size and Complexity: app.py",
    "objective": (
        "Measure and analyse the internal product attributes of app.py – a "
        "production Flask web application – using LOC, Halstead, and "
        "Cyclomatic Complexity metrics to evaluate code maintainability, "
        "documentation quality, and structural complexity."
    ),
    "hypotheses": [
        "H1: The comment density of app.py is below the recommended threshold "
        "of 0.20, indicating insufficient inline documentation.",
        "H2: The Halstead difficulty of app.py exceeds 30, suggesting the "
        "program requires significant mental effort to understand.",
        "H3: At least one function in app.py has a Cyclomatic Complexity "
        "greater than 10, indicating a high-risk maintenance area.",
    ],
    "investigation_technique": "Third-Degree Contact – static analysis of source code artifact",
    "independent_variables": ["Source file (app.py)", "Programming language (Python)"],
    "dependent_variables": [
        "LOC metrics (Total, Blank, Comment, Effective, Density)",
        "Halstead metrics (μ1, μ2, N1, N2, Vocabulary, Length, Volume, Difficulty, Effort)",
        "Cyclomatic Complexity per function",
    ],
}


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 2 – DATA COLLECTION: Metric Extractors
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class LOCMetrics:
    total_loc: int = 0
    blank_lines: int = 0
    comment_lines: int = 0   # CLOC
    effective_loc: int = 0   # NCLOC
    comment_density: float = 0.0


@dataclass
class HalsteadMetrics:
    distinct_operators: int = 0    # μ1
    distinct_operands: int = 0     # μ2
    total_operators: int = 0       # N1
    total_operands: int = 0        # N2
    vocabulary: int = 0            # μ = μ1 + μ2
    length: int = 0                # N = N1 + N2
    volume: float = 0.0            # V = N * log2(μ)
    difficulty: float = 0.0        # D = (μ1/2) * (N2/μ2)
    effort: float = 0.0            # E = D * V


@dataclass
class FunctionComplexity:
    name: str = ""
    cyclomatic_complexity: int = 1
    loc: int = 0
    start_line: int = 0
    risk_level: str = "Low"


@dataclass
class CollectedData:
    filepath: str = ""
    loc: LOCMetrics = field(default_factory=LOCMetrics)
    halstead: HalsteadMetrics = field(default_factory=HalsteadMetrics)
    functions: List[FunctionComplexity] = field(default_factory=list)
    class_count: int = 0
    function_count: int = 0
    import_count: int = 0


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 3 – DATA COLLECTION: Analyzer
# ──────────────────────────────────────────────────────────────────────────────

class EmpiricalDataCollector:
    """
    DC1: All measures are fully defined with counting rules.
    DC2: Tokenization errors are caught to ensure completeness.
    """

    def __init__(self, filepath: str):
        self.filepath = filepath
        with open(filepath, "r", encoding="utf-8") as f:
            self.source = f.read()
        self.lines = self.source.splitlines()

    # ── LOC ──────────────────────────────────────────────────────────────────

    def collect_loc(self) -> LOCMetrics:
        """
        Counting rules:
        - Blank lines  : line.strip() == ""
        - Comment lines: line.strip().startswith("#")  OR  "#" in line (inline)
        - NCLOC        : total - blank - comment_only lines
        - Comment density: CLOC / Total
        """
        total = len(self.lines)
        blank = sum(1 for l in self.lines if l.strip() == "")
        # Count lines that contain a # (includes inline comments)
        comment = sum(1 for l in self.lines if "#" in l)
        # NCLOC excludes blank AND pure-comment lines (not inline)
        pure_comment = sum(1 for l in self.lines if l.strip().startswith("#"))
        ncloc = total - blank - pure_comment
        density = round(comment / total, 4) if total else 0.0

        return LOCMetrics(
            total_loc=total,
            blank_lines=blank,
            comment_lines=comment,
            effective_loc=ncloc,
            comment_density=density,
        )

    # ── HALSTEAD ─────────────────────────────────────────────────────────────

    def collect_halstead(self) -> HalsteadMetrics:
        """
        Operators : tokenize.OP tokens
        Operands  : NAME, NUMBER, STRING tokens
        Derived   : Volume, Difficulty, Effort
        """
        operators: set = set()
        operands: set = set()
        n1 = n2 = 0

        try:
            tokens = tokenize.tokenize(BytesIO(self.source.encode("utf-8")).readline)
            for tok in tokens:
                if tok.type == tokenize.OP:
                    operators.add(tok.string)
                    n1 += 1
                elif tok.type in (tokenize.NAME, tokenize.NUMBER, tokenize.STRING):
                    operands.add(tok.string)
                    n2 += 1
        except tokenize.TokenError:
            pass  # DC2: prevent crash on malformed token

        mu1, mu2 = len(operators), len(operands)
        N = n1 + n2
        mu = mu1 + mu2

        volume     = round(N * math.log2(mu), 2)        if mu > 1 else 0.0
        difficulty = round((mu1 / 2) * (n2 / mu2), 2)  if mu2 > 0 else 0.0
        effort     = round(difficulty * volume, 2)

        return HalsteadMetrics(
            distinct_operators=mu1,
            distinct_operands=mu2,
            total_operators=n1,
            total_operands=n2,
            vocabulary=mu,
            length=N,
            volume=volume,
            difficulty=difficulty,
            effort=effort,
        )

    # ── CYCLOMATIC COMPLEXITY ─────────────────────────────────────────────────

    def collect_cyclomatic(self) -> List[FunctionComplexity]:
        """
        McCabe's Cyclomatic Complexity per function/method:
          CC = 1 + number of decision points
        Decision points: if, elif, for, while, except, with, assert, and, or
        Risk bands (SEI):
          1-10  → Low
          11-20 → Moderate
          21-50 → High
          >50   → Very High
        """
        decision_keywords = re.compile(
            r"\b(if|elif|for|while|except|with|assert)\b"
        )
        logical_ops = re.compile(r"\b(and|or)\b")
        results = []

        try:
            tree = ast.parse(self.source)
        except SyntaxError:
            return results

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Extract function source lines
                start = node.lineno
                end   = getattr(node, "end_lineno", start)
                func_lines = self.lines[start - 1: end]
                func_src   = "\n".join(func_lines)

                decisions = len(decision_keywords.findall(func_src))
                logicals  = len(logical_ops.findall(func_src))
                cc        = 1 + decisions + logicals
                loc       = end - start + 1

                risk = (
                    "Low"       if cc <= 10  else
                    "Moderate"  if cc <= 20  else
                    "High"      if cc <= 50  else
                    "Very High"
                )

                results.append(FunctionComplexity(
                    name=node.name,
                    cyclomatic_complexity=cc,
                    loc=loc,
                    start_line=start,
                    risk_level=risk,
                ))

        return sorted(results, key=lambda f: f.cyclomatic_complexity, reverse=True)

    # ── STRUCTURAL COUNTS ─────────────────────────────────────────────────────

    def collect_structure(self) -> Dict[str, int]:
        """Count classes, functions/methods, and imports."""
        try:
            tree = ast.parse(self.source)
        except SyntaxError:
            return {"classes": 0, "functions": 0, "imports": 0}

        classes   = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
        functions = sum(1 for n in ast.walk(tree)
                        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
        imports   = sum(1 for n in ast.walk(tree)
                        if isinstance(n, (ast.Import, ast.ImportFrom)))

        return {"classes": classes, "functions": functions, "imports": imports}

    # ── FULL COLLECTION ───────────────────────────────────────────────────────

    def collect_all(self) -> CollectedData:
        structure = self.collect_structure()
        data = CollectedData(
            filepath=self.filepath,
            loc=self.collect_loc(),
            halstead=self.collect_halstead(),
            functions=self.collect_cyclomatic(),
            class_count=structure["classes"],
            function_count=structure["functions"],
            import_count=structure["imports"],
        )
        return data


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 4 – ANALYSIS
# ──────────────────────────────────────────────────────────────────────────────

class EmpiricalAnalyzer:
    """
    A1: Hypothesis tests are pre-specified (no fishing).
    A2: Thresholds are industry-standard baselines.
    A3: Sensitivity noted in limitations.
    A4: Metrics computed from raw tokens – no distributional assumptions.
    """

    # Industry baselines used as comparison points
    BASELINE_COMMENT_DENSITY = 0.20    # recommended minimum
    BASELINE_HALSTEAD_DIFFICULTY = 30  # threshold for "hard to understand"
    BASELINE_CC_HIGH_RISK = 10         # SEI threshold for high-risk functions

    def __init__(self, data: CollectedData):
        self.data = data

    def test_h1_comment_density(self) -> Dict[str, Any]:
        """H1: comment density < 0.20 → insufficient documentation."""
        observed = self.data.loc.comment_density
        threshold = self.BASELINE_COMMENT_DENSITY
        supported = observed < threshold
        return {
            "hypothesis": "H1",
            "statement": "Comment density < 0.20 (insufficient documentation)",
            "observed_value": observed,
            "threshold": threshold,
            "supported": supported,
            "verdict": (
                f"SUPPORTED — density ({observed}) is below threshold ({threshold})."
                if supported else
                f"REFUTED — density ({observed}) meets or exceeds threshold ({threshold})."
            ),
        }

    def test_h2_halstead_difficulty(self) -> Dict[str, Any]:
        """H2: Halstead difficulty > 30 → high cognitive effort."""
        observed = self.data.halstead.difficulty
        threshold = self.BASELINE_HALSTEAD_DIFFICULTY
        supported = observed > threshold
        return {
            "hypothesis": "H2",
            "statement": "Halstead Difficulty > 30 (high cognitive effort required)",
            "observed_value": observed,
            "threshold": threshold,
            "supported": supported,
            "verdict": (
                f"SUPPORTED — difficulty ({observed}) exceeds threshold ({threshold})."
                if supported else
                f"REFUTED — difficulty ({observed}) does not exceed threshold ({threshold})."
            ),
        }

    def test_h3_cyclomatic_complexity(self) -> Dict[str, Any]:
        """H3: at least one function has CC > 10 → high-risk function exists."""
        high_risk = [f for f in self.data.functions
                     if f.cyclomatic_complexity > self.BASELINE_CC_HIGH_RISK]
        supported = len(high_risk) > 0
        return {
            "hypothesis": "H3",
            "statement": "At least one function has CC > 10 (high-risk maintenance area)",
            "observed_value": len(high_risk),
            "threshold": self.BASELINE_CC_HIGH_RISK,
            "supported": supported,
            "high_risk_functions": [(f.name, f.cyclomatic_complexity) for f in high_risk[:10]],
            "verdict": (
                f"SUPPORTED — {len(high_risk)} function(s) exceed CC threshold."
                if supported else
                "REFUTED — no functions exceed the CC threshold."
            ),
        }

    def descriptive_statistics_cc(self) -> Dict[str, Any]:
        """Descriptive stats for Cyclomatic Complexity distribution (P4)."""
        cc_values = [f.cyclomatic_complexity for f in self.data.functions]
        if not cc_values:
            return {}
        n = len(cc_values)
        mean = sum(cc_values) / n
        variance = sum((x - mean) ** 2 for x in cc_values) / n
        stddev = math.sqrt(variance)
        sorted_cc = sorted(cc_values)
        median = (
            sorted_cc[n // 2] if n % 2 == 1
            else (sorted_cc[n // 2 - 1] + sorted_cc[n // 2]) / 2
        )
        return {
            "n_functions": n,
            "mean_cc": round(mean, 2),
            "median_cc": round(median, 2),
            "std_cc": round(stddev, 2),
            "min_cc": min(cc_values),
            "max_cc": max(cc_values),
        }

    def run_all(self) -> Dict[str, Any]:
        return {
            "h1": self.test_h1_comment_density(),
            "h2": self.test_h2_halstead_difficulty(),
            "h3": self.test_h3_cyclomatic_complexity(),
            "cc_stats": self.descriptive_statistics_cc(),
        }


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 5 & 6 – PRESENTATION AND INTERPRETATION
# ──────────────────────────────────────────────────────────────────────────────

class EmpiricalReporter:
    """
    P1–P5: Structured output, raw data, descriptive stats, graphics (ASCII).
    I1–I3: Interpretation with limitations and statistical vs practical significance.
    """

    SEPARATOR = "=" * 70
    THIN_SEP  = "-" * 70

    def __init__(self, data: CollectedData, analysis: Dict[str, Any]):
        self.data = data
        self.analysis = analysis

    def _bar(self, value: float, max_val: float, width: int = 40) -> str:
        filled = int((value / max_val) * width) if max_val else 0
        return "█" * filled + "░" * (width - filled)

    # ── Print helpers ─────────────────────────────────────────────────────────

    def print_context(self):
        print(self.SEPARATOR)
        print("  EMPIRICAL SOFTWARE ENGINEERING INVESTIGATION")
        print("  Based on SENG 421 – Chapter 4 Framework")
        print(self.SEPARATOR)
        print(f"\n  Title    : {EXPERIMENT_CONTEXT['title']}")
        print(f"  File     : {self.data.filepath}")
        print(f"  Technique: {EXPERIMENT_CONTEXT['investigation_technique']}")
        print(f"\n  Objective:\n    {EXPERIMENT_CONTEXT['objective']}")
        print(f"\n  Hypotheses:")
        for h in EXPERIMENT_CONTEXT["hypotheses"]:
            print(f"    • {h}")
        print(f"\n  Independent Variables:")
        for v in EXPERIMENT_CONTEXT["independent_variables"]:
            print(f"    → {v}")
        print(f"\n  Dependent Variables:")
        for v in EXPERIMENT_CONTEXT["dependent_variables"]:
            print(f"    → {v}")

    def print_loc(self):
        loc = self.data.loc
        print(f"\n{self.THIN_SEP}")
        print("  [DC] DATA COLLECTED – LOC METRICS")
        print(self.THIN_SEP)
        rows = [
            ("Total LOC",           loc.total_loc),
            ("Blank Lines",         loc.blank_lines),
            ("Comment Lines (CLOC)",loc.comment_lines),
            ("Effective LOC (NCLOC)",loc.effective_loc),
        ]
        max_v = loc.total_loc or 1
        for label, val in rows:
            bar = self._bar(val, max_v)
            print(f"  {label:<28} {val:>6}  |{bar}|")
        print(f"\n  Comment Density : {loc.comment_density:.4f}"
              f"  (recommended ≥ 0.20)")

    def print_halstead(self):
        h = self.data.halstead
        print(f"\n{self.THIN_SEP}")
        print("  [DC] DATA COLLECTED – HALSTEAD METRICS")
        print(self.THIN_SEP)
        fields = [
            ("Distinct Operators (μ1)",  h.distinct_operators),
            ("Distinct Operands  (μ2)",  h.distinct_operands),
            ("Total Operators    (N1)",   h.total_operators),
            ("Total Operands     (N2)",   h.total_operands),
            ("Program Vocabulary (μ)",    h.vocabulary),
            ("Program Length     (N)",    h.length),
        ]
        for label, val in fields:
            print(f"  {label:<28} {val:>8}")
        print(f"\n  Derived Metrics:")
        print(f"  {'Volume    (V = N·log₂μ)':<28} {h.volume:>12.2f}")
        print(f"  {'Difficulty(D = μ1/2·N2/μ2)':<28} {h.difficulty:>12.2f}")
        print(f"  {'Effort    (E = D·V)':<28} {h.effort:>12.2f}")

    def print_cyclomatic(self):
        funcs = self.data.functions
        print(f"\n{self.THIN_SEP}")
        print("  [DC] DATA COLLECTED – CYCLOMATIC COMPLEXITY (Top 15 Functions)")
        print(self.THIN_SEP)
        print(f"  {'Function':<35} {'CC':>4}  {'LOC':>5}  {'Line':>5}  Risk")
        print(f"  {'-'*35} {'-'*4}  {'-'*5}  {'-'*5}  ----")
        for f in funcs[:15]:
            risk_icon = {"Low": "✔", "Moderate": "⚠", "High": "✘", "Very High": "✘✘"}.get(f.risk_level, "")
            print(f"  {f.name:<35} {f.cyclomatic_complexity:>4}  {f.loc:>5}  {f.start_line:>5}  "
                  f"{risk_icon} {f.risk_level}")

    def print_structure(self):
        print(f"\n{self.THIN_SEP}")
        print("  [DC] DATA COLLECTED – STRUCTURAL OVERVIEW")
        print(self.THIN_SEP)
        print(f"  Classes    : {self.data.class_count}")
        print(f"  Functions  : {self.data.function_count}")
        print(f"  Imports    : {self.data.import_count}")

    def print_analysis(self):
        print(f"\n{self.SEPARATOR}")
        print("  [A] ANALYSIS – HYPOTHESIS TESTING")
        print(self.SEPARATOR)
        for key in ("h1", "h2", "h3"):
            result = self.analysis[key]
            print(f"\n  {result['hypothesis']}: {result['statement']}")
            print(f"  {'Observed':<20} : {result['observed_value']}")
            print(f"  {'Threshold':<20} : {result['threshold']}")
            print(f"  {'Verdict':<20} : {result['verdict']}")

        stats = self.analysis.get("cc_stats", {})
        if stats:
            print(f"\n{self.THIN_SEP}")
            print("  [P4] DESCRIPTIVE STATISTICS – Cyclomatic Complexity")
            print(self.THIN_SEP)
            print(f"  Functions analysed : {stats['n_functions']}")
            print(f"  Mean CC            : {stats['mean_cc']}")
            print(f"  Median CC          : {stats['median_cc']}")
            print(f"  Std Dev CC         : {stats['std_cc']}")
            print(f"  Min CC             : {stats['min_cc']}")
            print(f"  Max CC             : {stats['max_cc']}")

    def print_cc_distribution(self):
        """ASCII histogram of CC distribution (P5 – graphics)."""
        cc_values = [f.cyclomatic_complexity for f in self.data.functions]
        if not cc_values:
            return
        buckets = {"1-5": 0, "6-10": 0, "11-20": 0, "21-50": 0, ">50": 0}
        for v in cc_values:
            if v <= 5:    buckets["1-5"]   += 1
            elif v <= 10: buckets["6-10"]  += 1
            elif v <= 20: buckets["11-20"] += 1
            elif v <= 50: buckets["21-50"] += 1
            else:         buckets[">50"]   += 1
        max_count = max(buckets.values()) or 1
        print(f"\n{self.THIN_SEP}")
        print("  [P5] CC DISTRIBUTION (ASCII Histogram)")
        print(self.THIN_SEP)
        for label, count in buckets.items():
            bar = self._bar(count, max_count, width=30)
            print(f"  CC {label:<6} |{bar}| {count}")

    def print_interpretation(self):
        """I1, I2, I3 – Interpretation, significance, limitations."""
        print(f"\n{self.SEPARATOR}")
        print("  [I] INTERPRETATION OF RESULTS")
        print(self.SEPARATOR)

        h1 = self.analysis["h1"]
        h2 = self.analysis["h2"]
        h3 = self.analysis["h3"]

        print(f"""
  I1 – Population:
    Results apply to app.py (Maternova Flask application) as a single
    Python module. Generalisation to other Flask projects requires
    replication across multiple codebases.

  I2 – Statistical vs Practical Significance:
    • H1 (Comment Density = {h1['observed_value']:.4f}):
      {"Below" if h1['supported'] else "Meets"} the 0.20 baseline.
      {"Practically significant: developers may struggle to understand"
       " undocumented sections." if h1['supported'] else
       "Practically acceptable documentation level."}

    • H2 (Halstead Difficulty = {h2['observed_value']:.2f}):
      {"Exceeds" if h2['supported'] else "Within"} the difficulty threshold of 30.
      {"High effort expected to comprehend or modify the codebase."
       if h2['supported'] else
       "Cognitive effort to maintain the codebase is within normal range."}

    • H3 ({h3['observed_value']} high-risk function(s)):
      {"High-risk functions detected — these are prime candidates for"
       " refactoring, unit-test coverage, and code review."
       if h3['supported'] else
       "No high-risk functions detected — good structural decomposition."}
      {"Top offenders: " + ", ".join(f[0] for f in h3.get("high_risk_functions", [])[:5])
       if h3['supported'] else ""}

  I3 – Limitations:
    • Comment detection uses '#' presence; multi-line docstrings
      (triple-quoted strings) are NOT counted as comments.
    • Cyclomatic Complexity is approximated via regex on source text;
      a full AST-based control-flow graph would be more precise.
    • Halstead metrics assume keyword-based operator/operand split;
      language-specific nuances (decorators, comprehensions) may skew counts.
    • This is a single-file, single-point-in-time measurement — no
      longitudinal or comparative data is available.
    • Results are not generalisable beyond this specific file without
      replicated studies (Principle: Replication).
""")

    def print_future_improvements(self):
        print(f"\n{self.THIN_SEP}")
        print("  FUTURE IMPROVEMENTS")
        print(self.THIN_SEP)
        improvements = [
            "Extend analysis to multiple files (multi-module investigation)",
            "Add docstring coverage metric (triple-quoted string detection)",
            "Implement full control-flow graph for precise Cyclomatic Complexity",
            "Integrate results into the Flask dashboard (app.py /metrics route)",
            "Add fan-in/fan-out coupling metrics",
            "Support longitudinal tracking across git commits",
            "Visualise results using matplotlib or plotly graphs",
        ]
        for i, item in enumerate(improvements, 1):
            print(f"  {i}. {item}")

    def report(self):
        self.print_context()
        self.print_structure()
        self.print_loc()
        self.print_halstead()
        self.print_cyclomatic()
        self.print_cc_distribution()
        self.print_analysis()
        self.print_interpretation()
        self.print_future_improvements()
        print(f"\n{self.SEPARATOR}")
        print("  END OF EMPIRICAL INVESTIGATION REPORT")
        print(self.SEPARATOR)


# ──────────────────────────────────────────────────────────────────────────────
# MAIN – Orchestrate the full investigation pipeline
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "app.py"

    # Phase 1 – Data Collection
    collector = EmpiricalDataCollector(target)
    data: CollectedData = collector.collect_all()

    # Phase 2 – Analysis
    analyzer = EmpiricalAnalyzer(data)
    results  = analyzer.run_all()

    # Phase 3 – Presentation & Interpretation
    reporter = EmpiricalReporter(data, results)
    reporter.report()
