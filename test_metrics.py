"""
test_metrics.py - Software Test Metrics for the MATERNOVA Project
==================================================================


Run with:
    python test_metrics.py            # full report
    python test_metrics.py --verbose  # detailed output
"""

import unittest
import time
import math
import json
import argparse
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple


class TestCaseEstimator:
    """
    Estimates the maximum number of test cases affordable given
    time and cost constraints.

    Formula (Slide 20):
      N_time = (available_weeks * hours_per_week * staff) / hours_per_case
      N_cost = (budget * test_fraction) / cost_per_case
      N = min(N_time, N_cost)
    """

    def __init__(
        self,
        budget: float,
        test_budget_fraction: float,
        cost_per_case: float,
        project_weeks: float,
        hours_per_week: float,
        staff: int,
        hours_per_case: float,
    ):
        self.budget = budget
        self.test_budget_fraction = test_budget_fraction
        self.cost_per_case = cost_per_case
        self.project_weeks = project_weeks
        self.hours_per_week = hours_per_week
        self.staff = staff
        self.hours_per_case = hours_per_case

    def n_from_cost(self) -> int:
        return int((self.budget * self.test_budget_fraction) / self.cost_per_case)

    def n_from_time(self) -> int:
        total_hours = self.project_weeks * self.hours_per_week * self.staff
        return int(total_hours / self.hours_per_case)

    def recommended_n(self) -> int:
        return min(self.n_from_cost(), self.n_from_time())

    def report(self) -> Dict:
        return {
            "n_from_cost": self.n_from_cost(),
            "n_from_time": self.n_from_time(),
            "recommended_n": self.recommended_n(),
            "binding_constraint": "cost" if self.n_from_cost() <= self.n_from_time() else "time",
        }




@dataclass
class CoverageResult:
    """Holds raw counts and the computed coverage percentage."""
    name: str
    tested: int
    total: int

    @property
    def percentage(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.tested / self.total) * 100.0

    def __str__(self):
        return f"{self.name}: {self.tested}/{self.total} = {self.percentage:.1f}%"


def statement_coverage(statements_tested: int, total_statements: int) -> CoverageResult:
    """CV_s = (S_t / S_p) * 100%  (Slide 46)"""
    return CoverageResult("Statement Coverage (CV_s)", statements_tested, total_statements)


def branch_coverage(branches_tested: int, total_branches: int) -> CoverageResult:
    """CV_b = (n_bt / n_b) * 100%  (Slide 47)"""
    return CoverageResult("Branch Coverage (CV_b)", branches_tested, total_branches)


def component_coverage(components_tested: int, total_components: int) -> CoverageResult:
    """CV_cm = (n_cmt / n_cm) * 100%  (Slide 48)"""
    return CoverageResult("Component Coverage (CV_cm)", components_tested, total_components)


def gui_coverage(gui_elements_tested: int, total_gui_elements: int) -> CoverageResult:
    """CV_GUI = (n_GUIt / n_GUI) * 100%  (Slide 49)"""
    return CoverageResult("GUI Coverage (CV_GUI)", gui_elements_tested, total_gui_elements)



@dataclass
class TestExecutionSummary:
    """
    Tracks how many test cases passed, failed, or are pending.

    R_tp   = (n_t_pass  / n_t_case) * 100%  (Slide 51)
    R_tf   = (n_t_fail  / n_t_case) * 100%  (Slide 52)
    R_tpend = (n_t_pend / n_t_case) * 100%  (Slide 53)
    """
    passed: int = 0
    failed: int = 0
    pending: int = 0

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.pending

    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total * 100) if self.total else 0.0

    @property
    def failure_rate(self) -> float:
        return (self.failed / self.total * 100) if self.total else 0.0

    @property
    def pending_rate(self) -> float:
        return (self.pending / self.total * 100) if self.total else 0.0

    def report(self) -> Dict:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "pending": self.pending,
            "pass_rate_%": round(self.pass_rate, 2),
            "failure_rate_%": round(self.failure_rate, 2),
            "pending_rate_%": round(self.pending_rate, 2),
        }



@dataclass
class BCS:
    """
    Branch Control Structure (BCS).

    A BCS is independently determinable (ID_BCS) when its Boolean
    variables depend only on the component's direct inputs {I}.
    TC_BCS = 1 if independently determinable, else 0.  (Slide 57)
    """
    name: str
    independently_determinable: bool

    @property
    def tc_bcs(self) -> int:
        return 1 if self.independently_determinable else 0


def component_testability(bcs_list: List[BCS]) -> float:
    """
    TC = (1/n) * sum(TC_BCSi)   (Slide 58)
    TC = 1.0 means fully controllable.
    """
    if not bcs_list:
        return 0.0
    return sum(b.tc_bcs for b in bcs_list) / len(bcs_list)



def estimate_remaining_defects_seeding(
    N_s: int,   # total seeded faults injected
    n_s: int,   # seeded faults detected during test
    n_d: int,   # non-seeded (real) faults detected during test
) -> Dict:
    """
    Mills 1972 fault seeding method.

    N_d = (n_d / n_s) * N_s          — estimated total real defects
    N_r = (N_d - n_d) + (N_s - n_s) — undetected remaining defects
    (Slides 62-63)
    """
    if n_s == 0:
        raise ValueError("n_s (detected seeded faults) cannot be zero")
    N_d = (n_d / n_s) * N_s
    N_r = (N_d - n_d) + (N_s - n_s)
    return {
        "N_s_total_seeded": N_s,
        "n_s_detected_seeded": n_s,
        "n_d_detected_real": n_d,
        "N_d_estimated_total_real": round(N_d, 2),
        "N_r_undetected_remaining": round(N_r, 2),
    }



def estimate_remaining_defects_comparative(
    d1: int,   # defects found by Team 1
    d2: int,   # defects found by Team 2
    d12: int,  # defects found by BOTH teams
) -> Dict:
    """
    Two-team comparative method.

    N_d = (d1 * d2) / d12
    N_r = N_d - (d1 + d2 - d12)
    (Slides 64-65)
    """
    if d12 == 0:
        raise ValueError("d12 (defects found by both teams) cannot be zero")
    N_d = (d1 * d2) / d12
    N_r = N_d - (d1 + d2 - d12)
    return {
        "d1_team1": d1,
        "d2_team2": d2,
        "d12_both": d12,
        "N_d_estimated_total": round(N_d, 2),
        "N_r_undetected_remaining": round(N_r, 2),
    }



@dataclass
class Phase:
    name: str
    defects_introduced: int
    defects_found: int
    defects_removed: int
    defects_carried_in: int = 0  # existing defects entering this phase


def phase_containment_effectiveness(phase: Phase) -> float:
    """
    PCE = (defects_removed / (defects_carried_in + defects_introduced)) * 100%
    Higher PCE = fewer defects pushed to later phases. (Slide 66-67)
    """
    denominator = phase.defects_carried_in + phase.defects_introduced
    if denominator == 0:
        return 0.0
    return (phase.defects_removed / denominator) * 100.0


def pce_pipeline(phases: List[Phase]) -> List[Dict]:
    """
    Computes PCE for each phase and automatically carries forward
    unresolved defects to the next phase.
    """
    results = []
    carry = 0
    for ph in phases:
        ph.defects_carried_in = carry
        pce = phase_containment_effectiveness(ph)
        unresolved = ph.defects_carried_in + ph.defects_introduced - ph.defects_removed
        results.append({
            "phase": ph.name,
            "carried_in": ph.defects_carried_in,
            "introduced": ph.defects_introduced,
            "found": ph.defects_found,
            "removed": ph.defects_removed,
            "PCE_%": round(pce, 2),
            "pushed_forward": max(0, unresolved),
        })
        carry = max(0, unresolved)
    return results


# =============================================================================
# 8.  MATERNOVA-SPECIFIC TEST CASES
#     Applied to a typical Flask/SQLAlchemy maternal-health web app
#     (routes: /register, /login, /dashboard, /record, /report)
# =============================================================================

class MaternovalInputValidationTests(unittest.TestCase):
    """
    Equivalence-class & boundary-value test cases (Slides 22-28)
    for typical MATERNOVA form fields.
    """

    # ------------------------------------------------------------------ #
    # Helper – simulate route-level validation without a running server   #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _validate_gestational_age(weeks) -> Tuple[bool, str]:
        """Gestational age: integer, 1–42 weeks inclusive."""
        if isinstance(weeks, float):
            return False, "not_integer"
        try:
            w = int(weeks)
        except (TypeError, ValueError):
            return False, "not_integer"
        if w < 1:
            return False, "below_min"
        if w > 42:
            return False, "above_max"
        return True, "ok"

    @staticmethod
    def _validate_blood_pressure(systolic, diastolic) -> Tuple[bool, str]:
        """
        Systolic: 60–250 mmHg, Diastolic: 40–150 mmHg.
        Diastolic must be < Systolic.
        """
        try:
            s, d = int(systolic), int(diastolic)
        except (TypeError, ValueError):
            return False, "not_integer"
        if not (60 <= s <= 250):
            return False, "systolic_out_of_range"
        if not (40 <= d <= 150):
            return False, "diastolic_out_of_range"
        if d >= s:
            return False, "diastolic_gte_systolic"
        return True, "ok"

    @staticmethod
    def _validate_weight_kg(weight) -> Tuple[bool, str]:
        """Maternal weight: 30.0–200.0 kg."""
        try:
            w = float(weight)
        except (TypeError, ValueError):
            return False, "not_numeric"
        if w < 30.0:
            return False, "below_min"
        if w > 200.0:
            return False, "above_max"
        return True, "ok"

    # ------------------------------------------------------------------ #
    # Gestational age – equivalence classes                   #
    # ------------------------------------------------------------------ #
    def test_ga_valid_range(self):
        """Equivalence class: valid gestational age (1–42)."""
        for v in [1, 20, 42]:
            ok, _ = self._validate_gestational_age(v)
            self.assertTrue(ok, f"Expected valid for ga={v}")

    def test_ga_below_minimum(self):
        """Equivalence class: GA below 1 week – should fail."""
        ok, reason = self._validate_gestational_age(0)
        self.assertFalse(ok)
        self.assertEqual(reason, "below_min")

    def test_ga_above_maximum(self):
        """Equivalence class: GA above 42 weeks – should fail."""
        ok, reason = self._validate_gestational_age(43)
        self.assertFalse(ok)
        self.assertEqual(reason, "above_max")

    def test_ga_non_integer(self):
        """Equivalence class: non-integer input – should fail."""
        for v in ["abc", None, "", 12.5]:
            ok, reason = self._validate_gestational_age(v)
            self.assertFalse(ok)

    # Boundary conditions (Slide 28)
    def test_ga_boundary_lower(self):
        """Boundary: exactly 1 week should pass."""
        ok, _ = self._validate_gestational_age(1)
        self.assertTrue(ok)

    def test_ga_boundary_upper(self):
        """Boundary: exactly 42 weeks should pass."""
        ok, _ = self._validate_gestational_age(42)
        self.assertTrue(ok)

    def test_ga_boundary_just_below(self):
        """Boundary: 0 weeks should fail."""
        ok, _ = self._validate_gestational_age(0)
        self.assertFalse(ok)

    def test_ga_boundary_just_above(self):
        """Boundary: 43 weeks should fail."""
        ok, _ = self._validate_gestational_age(43)
        self.assertFalse(ok)

    # ------------------------------------------------------------------ #
    # Blood pressure                                                      #
    # ------------------------------------------------------------------ #
    def test_bp_valid(self):
        """Equivalence class: valid BP reading."""
        ok, _ = self._validate_blood_pressure(120, 80)
        self.assertTrue(ok)

    def test_bp_systolic_too_low(self):
        ok, reason = self._validate_blood_pressure(59, 40)
        self.assertFalse(ok)
        self.assertEqual(reason, "systolic_out_of_range")

    def test_bp_systolic_too_high(self):
        ok, reason = self._validate_blood_pressure(251, 80)
        self.assertFalse(ok)
        self.assertEqual(reason, "systolic_out_of_range")

    def test_bp_diastolic_gte_systolic(self):
        """Diastolic ≥ systolic is physiologically impossible."""
        ok, reason = self._validate_blood_pressure(100, 110)
        self.assertFalse(ok)
        self.assertEqual(reason, "diastolic_gte_systolic")

    def test_bp_boundary_systolic_min(self):
        ok, _ = self._validate_blood_pressure(60, 40)
        self.assertTrue(ok)

    def test_bp_boundary_systolic_max(self):
        ok, _ = self._validate_blood_pressure(250, 100)
        self.assertTrue(ok)

    # ------------------------------------------------------------------ #
    # Weight                                                              #
    # ------------------------------------------------------------------ #
    def test_weight_valid(self):
        ok, _ = self._validate_weight_kg(65.0)
        self.assertTrue(ok)

    def test_weight_below_min(self):
        ok, reason = self._validate_weight_kg(29.9)
        self.assertFalse(ok)
        self.assertEqual(reason, "below_min")

    def test_weight_above_max(self):
        ok, reason = self._validate_weight_kg(200.1)
        self.assertFalse(ok)
        self.assertEqual(reason, "above_max")

    def test_weight_non_numeric(self):
        ok, _ = self._validate_weight_kg("heavy")
        self.assertFalse(ok)

    def test_weight_boundary_lower(self):
        ok, _ = self._validate_weight_kg(30.0)
        self.assertTrue(ok)

    def test_weight_boundary_upper(self):
        ok, _ = self._validate_weight_kg(200.0)
        self.assertTrue(ok)


class MaternovalMetricCalculationTests(unittest.TestCase):
    """Unit tests for the metric utility functions in this module."""

    # ------------------------------------------------------------------ #
    # Test Case Estimator                                                 #
    # ------------------------------------------------------------------ #
    def test_estimator_textbook_example(self):
        """Reproduces the slide 21 textbook example: N=1250."""
        est = TestCaseEstimator(
            budget=4_000_000, test_budget_fraction=0.10,
            cost_per_case=250, project_weeks=25,
            hours_per_week=40, staff=5, hours_per_case=4,
        )
        self.assertEqual(est.n_from_cost(), 1600)
        self.assertEqual(est.n_from_time(), 1250)
        self.assertEqual(est.recommended_n(), 1250)
        self.assertEqual(est.report()["binding_constraint"], "time")

    def test_estimator_cost_bound(self):
        """When budget is tight, cost should be the binding constraint."""
        est = TestCaseEstimator(
            budget=100_000, test_budget_fraction=0.05,
            cost_per_case=500, project_weeks=52,
            hours_per_week=40, staff=10, hours_per_case=2,
        )
        self.assertLessEqual(est.recommended_n(), est.n_from_time())

    # ------------------------------------------------------------------ #
    # Coverage metrics                                                    #
    # ------------------------------------------------------------------ #
    def test_statement_coverage_full(self):
        r = statement_coverage(100, 100)
        self.assertAlmostEqual(r.percentage, 100.0)

    def test_statement_coverage_partial(self):
        r = statement_coverage(75, 100)
        self.assertAlmostEqual(r.percentage, 75.0)

    def test_branch_coverage(self):
        r = branch_coverage(8, 10)
        self.assertAlmostEqual(r.percentage, 80.0)

    def test_component_coverage(self):
        r = component_coverage(5, 5)
        self.assertAlmostEqual(r.percentage, 100.0)

    def test_gui_coverage(self):
        r = gui_coverage(12, 15)
        self.assertAlmostEqual(r.percentage, 80.0)

    def test_zero_total_returns_zero(self):
        r = statement_coverage(0, 0)
        self.assertEqual(r.percentage, 0.0)

    # ------------------------------------------------------------------ #
    # Pass / failure / pending rates                                      #
    # ------------------------------------------------------------------ #
    def test_execution_summary_rates(self):
        s = TestExecutionSummary(passed=80, failed=15, pending=5)
        self.assertAlmostEqual(s.pass_rate, 80.0)
        self.assertAlmostEqual(s.failure_rate, 15.0)
        self.assertAlmostEqual(s.pending_rate, 5.0)
        self.assertEqual(s.total, 100)

    def test_execution_summary_zero(self):
        s = TestExecutionSummary()
        self.assertEqual(s.pass_rate, 0.0)

    # ------------------------------------------------------------------ #
    # Software testability (TC)                                           #
    # ------------------------------------------------------------------ #
    def test_tc_example1_slide59(self):
        """Reproduces Example 1 on slide 59: TC=0.33."""
        bcs = [
            BCS("BCS1_if_else", True),
            BCS("BCS2_case", False),
            BCS("BCS3_if_else", False),
        ]
        tc = component_testability(bcs)
        self.assertAlmostEqual(tc, 1/3, places=2)

    def test_tc_fully_controllable(self):
        bcs = [BCS(f"b{i}", True) for i in range(5)]
        self.assertAlmostEqual(component_testability(bcs), 1.0)

    def test_tc_not_controllable(self):
        bcs = [BCS(f"b{i}", False) for i in range(4)]
        self.assertAlmostEqual(component_testability(bcs), 0.0)

    def test_tc_example2_slide60(self):
        """Reproduces Example 2 on slide 60: TC=0.33."""
        bcs = [
            BCS("C1", True), BCS("C2", True),
            BCS("C3", False), BCS("C4", False),
            BCS("C5", False), BCS("C6", False),
        ]
        self.assertAlmostEqual(component_testability(bcs), 1/3, places=2)

    # ------------------------------------------------------------------ #
    # Remaining defects – fault seeding                                   #
    # ------------------------------------------------------------------ #
    def test_seeding_textbook_example_slide63(self):
        """Slide 63: N_s=20, n_s=10, n_d=50 → N_d=100, N_r=60."""
        r = estimate_remaining_defects_seeding(N_s=20, n_s=10, n_d=50)
        self.assertAlmostEqual(r["N_d_estimated_total_real"], 100.0)
        self.assertAlmostEqual(r["N_r_undetected_remaining"], 60.0)

    def test_seeding_zero_detected_raises(self):
        with self.assertRaises(ValueError):
            estimate_remaining_defects_seeding(N_s=20, n_s=0, n_d=50)

    def test_seeding_all_detected(self):
        """If n_s == N_s and n_d == N_d, then N_r should be 0."""
        r = estimate_remaining_defects_seeding(N_s=10, n_s=10, n_d=30)
        # N_d = (30/10)*10 = 30; N_r = (30-30)+(10-10) = 0
        self.assertAlmostEqual(r["N_r_undetected_remaining"], 0.0)

    # ------------------------------------------------------------------ #
    # Remaining defects – comparative method                              #
    # ------------------------------------------------------------------ #
    def test_comparative_textbook_slide65(self):
        """Slide 65: d1=50, d2=40, d12=20 → N_d=100, N_r=30."""
        r = estimate_remaining_defects_comparative(d1=50, d2=40, d12=20)
        self.assertAlmostEqual(r["N_d_estimated_total"], 100.0)
        self.assertAlmostEqual(r["N_r_undetected_remaining"], 30.0)

    def test_comparative_zero_overlap_raises(self):
        with self.assertRaises(ValueError):
            estimate_remaining_defects_comparative(d1=10, d2=10, d12=0)

    # ------------------------------------------------------------------ #
    # Phase Containment Effectiveness                                     #
    # ------------------------------------------------------------------ #
    def test_pce_textbook_example_slide67(self):
        """
        Slide 67 example:
          Req:    intro=12, found=9,  removed=9   → PCE = 75%
          Design: intro=25, found=16, removed=12  → PCE ≈ 42.85%
          Coding: intro=47, found=42, removed=36  → PCE ≈ 57.14%
        """
        phases = [
            Phase("Requirements", defects_introduced=12, defects_found=9, defects_removed=9),
            Phase("Design",       defects_introduced=25, defects_found=16, defects_removed=12),
            Phase("Coding",       defects_introduced=47, defects_found=42, defects_removed=36),
        ]
        results = pce_pipeline(phases)

        self.assertAlmostEqual(results[0]["PCE_%"], 75.0, places=1)
        self.assertAlmostEqual(results[1]["PCE_%"], 42.86, places=1)
        self.assertAlmostEqual(results[2]["PCE_%"], 57.14, places=1)

    def test_pce_perfect_phase(self):
        """A phase that removes all introduced defects should have PCE=100%."""
        phase = Phase("Test", defects_introduced=10, defects_found=10, defects_removed=10)
        self.assertAlmostEqual(phase_containment_effectiveness(phase), 100.0)

    def test_pce_zero_introduced(self):
        phase = Phase("Empty", defects_introduced=0, defects_found=0, defects_removed=0)
        self.assertEqual(phase_containment_effectiveness(phase), 0.0)

    def test_pce_carry_forward(self):
        """Defects not removed in phase N should carry into phase N+1."""
        phases = [
            Phase("A", defects_introduced=10, defects_found=6, defects_removed=6),
            Phase("B", defects_introduced=5,  defects_found=5, defects_removed=5),
        ]
        results = pce_pipeline(phases)
        # Phase A removes 6/10 → 4 carry forward
        self.assertEqual(results[1]["carried_in"], 4)


# =============================================================================
# 9. FULL METRICS REPORT  (printed when run as __main__)
# =============================================================================

def run_full_report(verbose: bool = False) -> Dict:
    """
    Produces a complete software test metrics report for the MATERNOVA
    project using representative (placeholder) data.  Replace with real
    measurements from your test runner and static-analysis tools.
    """
    report = {}

    # ── 1. Test case budget ────────────────────────────────────────────
    est = TestCaseEstimator(
        budget=50_000, test_budget_fraction=0.12,
        cost_per_case=30, project_weeks=16,
        hours_per_week=40, staff=3, hours_per_case=2,
    )
    report["test_case_estimate"] = est.report()

    # ── 2. Coverage (replace with real numbers from coverage.py) ───────
    coverage = {
        "statement":  statement_coverage(312, 415),
        "branch":     branch_coverage(88, 124),
        "component":  component_coverage(9, 12),
        "gui":        gui_coverage(27, 34),
    }
    report["coverage"] = {k: {"tested": v.tested, "total": v.total,
                               "percentage_%": round(v.percentage, 2)}
                          for k, v in coverage.items()}

    # ── 3. Test execution summary ───────────────────────────────────────
    exec_summary = TestExecutionSummary(passed=41, failed=6, pending=3)
    report["execution_summary"] = exec_summary.report()

    # ── 4. Testability ──────────────────────────────────────────────────
    app_bcs = [
        BCS("login_auth_check",         True),   # depends only on form inputs
        BCS("session_active_check",      False),  # depends on session state
        BCS("role_permission_check",     False),  # depends on DB query result
        BCS("date_range_filter",         True),
        BCS("record_duplicate_check",    False),
        BCS("bp_threshold_alert",        True),
        BCS("weight_trend_alert",        False),
    ]
    tc = component_testability(app_bcs)
    report["testability"] = {
        "TC": round(tc, 3),
        "fully_controllable_bcs": sum(b.tc_bcs for b in app_bcs),
        "total_bcs": len(app_bcs),
        "interpretation": "Good (> 0.5)" if tc > 0.5 else
                          "Moderate (0.33–0.5)" if tc >= 0.33 else "Low (< 0.33)",
    }

    # ── 5. Remaining defects (fault seeding) ───────────────────────────
    seeding = estimate_remaining_defects_seeding(N_s=15, n_s=9, n_d=24)
    report["remaining_defects_seeding"] = seeding

    # ── 6. Remaining defects (comparative) ─────────────────────────────
    comparative = estimate_remaining_defects_comparative(d1=24, d2=18, d12=10)
    report["remaining_defects_comparative"] = comparative

    # ── 7. Phase containment ────────────────────────────────────────────
    phases = [
        Phase("Requirements", defects_introduced=8,  defects_found=6,  defects_removed=6),
        Phase("Design",       defects_introduced=14, defects_found=9,  defects_removed=8),
        Phase("Implementation",defects_introduced=22,defects_found=17, defects_removed=15),
        Phase("Testing",      defects_introduced=3,  defects_found=18, defects_removed=18),
    ]
    report["pce_pipeline"] = pce_pipeline(phases)

    return report


def print_report(report: Dict):
    separator = "=" * 65

    print(f"\n{separator}")
    print("  MATERNOVA – Software Test Metrics Report (SENG 421 Ch.10)")
    print(separator)

    # 1
    est = report["test_case_estimate"]
    print("\n[1] TEST CASE ESTIMATION")
    print(f"    N from cost constraint : {est['n_from_cost']}")
    print(f"    N from time constraint : {est['n_from_time']}")
    print(f"    Recommended N          : {est['recommended_n']}  "
          f"(binding = {est['binding_constraint']})")

    # 2
    print("\n[2] COVERAGE METRICS")
    for k, v in report["coverage"].items():
        print(f"    {k:<12}: {v['tested']}/{v['total']} = {v['percentage_%']}%")

    # 3
    s = report["execution_summary"]
    print("\n[3] TEST EXECUTION SUMMARY")
    print(f"    Total test cases : {s['total']}")
    print(f"    Pass rate        : {s['pass_rate_%']}%")
    print(f"    Failure rate     : {s['failure_rate_%']}%")
    print(f"    Pending rate     : {s['pending_rate_%']}%")

    # 4
    t = report["testability"]
    print("\n[4] SOFTWARE TESTABILITY")
    print(f"    TC = {t['TC']}  "
          f"({t['fully_controllable_bcs']}/{t['total_bcs']} BCSs controllable)")
    print(f"    Assessment : {t['interpretation']}")

    # 5
    sd = report["remaining_defects_seeding"]
    print("\n[5] REMAINING DEFECTS  (Fault Seeding Method)")
    print(f"    Seeded injected / detected : {sd['N_s_total_seeded']} / {sd['n_s_detected_seeded']}")
    print(f"    Real defects detected      : {sd['n_d_detected_real']}")
    print(f"    Estimated total real (N_d) : {sd['N_d_estimated_total_real']}")
    print(f"    Undetected remaining (N_r) : {sd['N_r_undetected_remaining']}")

    # 6
    cd = report["remaining_defects_comparative"]
    print("\n[6] REMAINING DEFECTS  (Comparative Method)")
    print(f"    Team1={cd['d1_team1']}  Team2={cd['d2_team2']}  Both={cd['d12_both']}")
    print(f"    Estimated total (N_d)      : {cd['N_d_estimated_total']}")
    print(f"    Undetected remaining (N_r) : {cd['N_r_undetected_remaining']}")

    # 7
    print("\n[7] PHASE CONTAINMENT EFFECTIVENESS (PCE)")
    print(f"    {'Phase':<18} {'Carry-in':>8} {'Intro':>6} {'Removed':>8} "
          f"{'PCE %':>7} {'Pushed→':>8}")
    print(f"    {'-'*60}")
    for p in report["pce_pipeline"]:
        print(f"    {p['phase']:<18} {p['carried_in']:>8} {p['introduced']:>6} "
              f"{p['removed']:>8} {p['PCE_%']:>7.2f} {p['pushed_forward']:>8}")

    print(f"\n{separator}\n")


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="MATERNOVA Software Test Metrics (SENG 421 Ch.10)"
    )
    parser.add_argument("--test", action="store_true",
                        help="Run the unittest suite only")
    parser.add_argument("--report", action="store_true",
                        help="Print the metrics report only")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose unittest output")
    args = parser.parse_args()

    run_tests = args.test or not args.report
    run_report = args.report or not args.test

    if run_tests:
        print("Running test suite …\n")
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        suite.addTests(loader.loadTestsFromTestCase(MaternovalInputValidationTests))
        suite.addTests(loader.loadTestsFromTestCase(MaternovalMetricCalculationTests))
        verbosity = 2 if args.verbose else 1
        runner = unittest.TextTestRunner(verbosity=verbosity)
        result = runner.run(suite)

    if run_report:
        data = run_full_report()
        print_report(data)

    # Exit with non-zero if tests failed
    if run_tests and not result.wasSuccessful():
        sys.exit(1)
