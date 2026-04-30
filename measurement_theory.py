"""
measurement_theory.py
This module applies Measurement Theory to the Maternova maternal health system.
It defines how clinical variables are measured, what scale they belong to,
and provides functions to validate, classify, and summarize patient data.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Any
from collections import Counter


# Measurement scales based on Stevens (1946)
# Nominal = categories only, Ordinal = ordered categories,
# Interval = equal gaps but no true zero, Ratio = equal gaps with true zero

class MeasurementScale(Enum):
    NOMINAL = "nominal"
    ORDINAL = "ordinal"
    INTERVAL = "interval"
    RATIO = "ratio"


# This class describes each measurable variable in the system
@dataclass
class MeasurementVariable:
    name: str
    db_field: str
    scale: MeasurementScale
    unit: Optional[str] = None
    precision: Optional[int] = None
    valid_range: Optional[tuple] = None
    allowed_values: Optional[List[str]] = None


# Defining all the variables we measure in Maternova

GENDER = MeasurementVariable(
    name="Gender",
    db_field="gender",
    scale=MeasurementScale.NOMINAL,
    allowed_values=["Female", "Male"]
)

BLOOD_TYPE = MeasurementVariable(
    name="Blood Type",
    db_field="blood_type",
    scale=MeasurementScale.NOMINAL,
    allowed_values=["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]
)

BP_SYSTOLIC = MeasurementVariable(
    name="Systolic Blood Pressure",
    db_field="blood_pressure_systolic",
    scale=MeasurementScale.RATIO,
    unit="mmHg",
    precision=0,
    valid_range=(50, 260)
)

BP_DIASTOLIC = MeasurementVariable(
    name="Diastolic Blood Pressure",
    db_field="blood_pressure_diastolic",
    scale=MeasurementScale.RATIO,
    unit="mmHg",
    precision=0,
    valid_range=(30, 160)
)

HEART_RATE = MeasurementVariable(
    name="Heart Rate",
    db_field="heart_rate",
    scale=MeasurementScale.RATIO,
    unit="bpm",
    precision=0,
    valid_range=(20, 250)
)

# Temperature is interval not ratio because 0 degrees C is not absence of heat
TEMPERATURE = MeasurementVariable(
    name="Body Temperature",
    db_field="temperature",
    scale=MeasurementScale.INTERVAL,
    unit="C",
    precision=1,
    valid_range=(32.0, 43.0)
)

WEIGHT = MeasurementVariable(
    name="Body Weight",
    db_field="weight",
    scale=MeasurementScale.RATIO,
    unit="kg",
    precision=1,
    valid_range=(20.0, 250.0)
)

RESPIRATORY_RATE = MeasurementVariable(
    name="Respiratory Rate",
    db_field="respiratory_rate",
    scale=MeasurementScale.RATIO,
    unit="breaths/min",
    precision=0,
    valid_range=(4, 60)
)

OXYGEN_SATURATION = MeasurementVariable(
    name="Oxygen Saturation",
    db_field="oxygen_saturation",
    scale=MeasurementScale.RATIO,
    unit="%",
    precision=0,
    valid_range=(50, 100)
)

GESTATIONAL_WEEKS = MeasurementVariable(
    name="Gestational Age",
    db_field="gestational_weeks",
    scale=MeasurementScale.RATIO,
    unit="weeks",
    precision=0,
    valid_range=(0, 45)
)

GRAVIDA = MeasurementVariable(
    name="Gravida",
    db_field="gravida",
    scale=MeasurementScale.RATIO,
    unit="count",
    precision=0,
    valid_range=(0, 20)
)

PARA = MeasurementVariable(
    name="Para",
    db_field="para",
    scale=MeasurementScale.RATIO,
    unit="count",
    precision=0,
    valid_range=(0, 20)
)

# Risk level is ordinal because High > Moderate > Low but the gaps are not equal
RISK_LEVEL = MeasurementVariable(
    name="Pregnancy Risk Level",
    db_field="risk_level",
    scale=MeasurementScale.ORDINAL,
    allowed_values=["Low", "Moderate", "High"]
)

APPOINTMENT_STATUS = MeasurementVariable(
    name="Appointment Status",
    db_field="status",
    scale=MeasurementScale.NOMINAL,
    allowed_values=["scheduled", "completed", "cancelled"]
)

# putting all variables in one dictionary for easy lookup
ALL_VARIABLES = {
    v.db_field: v for v in [
        GENDER, BLOOD_TYPE, BP_SYSTOLIC, BP_DIASTOLIC,
        HEART_RATE, TEMPERATURE, WEIGHT, RESPIRATORY_RATE,
        OXYGEN_SATURATION, GESTATIONAL_WEEKS, GRAVIDA,
        PARA, RISK_LEVEL, APPOINTMENT_STATUS
    ]
}


@dataclass
class ValidationResult:
    is_valid: bool
    field: str
    value: Any
    message: str = ""


def validate_value(variable, value):
    if value is None:
        return ValidationResult(
            is_valid=False,
            field=variable.db_field,
            value=value,
            message=f"{variable.name} has no value recorded."
        )

    if variable.scale in (MeasurementScale.NOMINAL, MeasurementScale.ORDINAL):
        if variable.allowed_values and value not in variable.allowed_values:
            return ValidationResult(
                is_valid=False,
                field=variable.db_field,
                value=value,
                message=f"{value} is not valid for {variable.name}. Should be one of: {variable.allowed_values}"
            )

    if variable.scale in (MeasurementScale.RATIO, MeasurementScale.INTERVAL):
        if variable.valid_range:
            lo, hi = variable.valid_range
            try:
                num = float(value)
            except (TypeError, ValueError):
                return ValidationResult(
                    is_valid=False,
                    field=variable.db_field,
                    value=value,
                    message=f"{variable.name} should be a number."
                )
            if not (lo <= num <= hi):
                return ValidationResult(
                    is_valid=False,
                    field=variable.db_field,
                    value=value,
                    message=f"{variable.name} value {num} {variable.unit} is outside the expected range ({lo} to {hi})."
                )

    return ValidationResult(is_valid=True, field=variable.db_field, value=value)


def validate_vital_sign(vital):
    checks = [
        (BP_SYSTOLIC,       vital.blood_pressure_systolic),
        (BP_DIASTOLIC,      vital.blood_pressure_diastolic),
        (HEART_RATE,        vital.heart_rate),
        (TEMPERATURE,       vital.temperature),
        (WEIGHT,            vital.weight),
        (RESPIRATORY_RATE,  vital.respiratory_rate),
        (OXYGEN_SATURATION, vital.oxygen_saturation),
    ]
    errors = []
    for var, val in checks:
        result = validate_value(var, val)
        if not result.is_valid:
            errors.append(result)
    return errors


def validate_pregnancy_record(preg):
    checks = [
        (GESTATIONAL_WEEKS, preg.gestational_weeks),
        (GRAVIDA,           preg.gravida),
        (PARA,              preg.para),
        (RISK_LEVEL,        preg.risk_level),
    ]
    errors = []
    for var, val in checks:
        result = validate_value(var, val)
        if not result.is_valid:
            errors.append(result)
    return errors


# Classification functions
# These convert raw numbers into categories (ratio to ordinal transformation)

class BPCategory(Enum):
    NORMAL = "Normal"
    ELEVATED = "Elevated"
    HIGH = "High"
    CRITICAL = "Critical"


def classify_blood_pressure(systolic):
    if systolic is None:
        return None
    if systolic >= 160:
        return BPCategory.CRITICAL
    if systolic >= 140:
        return BPCategory.HIGH
    if systolic >= 120:
        return BPCategory.ELEVATED
    return BPCategory.NORMAL


class HeartRateCategory(Enum):
    BRADYCARDIA = "Bradycardia"
    NORMAL = "Normal"
    TACHYCARDIA = "Tachycardia"


def classify_heart_rate(hr):
    if hr is None:
        return None
    if hr < 55:
        return HeartRateCategory.BRADYCARDIA
    if hr > 100:
        return HeartRateCategory.TACHYCARDIA
    return HeartRateCategory.NORMAL


class TemperatureCategory(Enum):
    HYPOTHERMIA = "Hypothermia"
    NORMAL = "Normal"
    FEVER = "Fever"


def classify_temperature(temp):
    if temp is None:
        return None
    if temp < 36.0:
        return TemperatureCategory.HYPOTHERMIA
    if temp >= 38.0:
        return TemperatureCategory.FEVER
    return TemperatureCategory.NORMAL


class OxygenCategory(Enum):
    CRITICAL = "Critical"
    LOW = "Low"
    NORMAL = "Normal"


def classify_oxygen_saturation(spo2):
    if spo2 is None:
        return None
    if spo2 < 90:
        return OxygenCategory.CRITICAL
    if spo2 < 95:
        return OxygenCategory.LOW
    return OxygenCategory.NORMAL


# Used for sorting/comparing risk levels since they are ordinal
RISK_LEVEL_ORDER = {"Low": 0, "Moderate": 1, "High": 2}

def risk_level_to_int(risk_level):
    return RISK_LEVEL_ORDER.get(risk_level, -1)


# Aggregate statistics
# Only computes what is allowed for each scale type

def aggregate_vitals(vitals_list, field):
    variable = ALL_VARIABLES.get(field)
    if variable is None:
        return {"error": f"Field '{field}' not found"}

    values = [getattr(v, field) for v in vitals_list if getattr(v, field) is not None]
    if not values:
        return {"field": field, "count": 0, "note": "No data recorded"}

    result = {"field": field, "unit": variable.unit, "count": len(values)}

    freq = Counter(values)
    result["mode"] = freq.most_common(1)[0][0]

    if variable.scale in (MeasurementScale.ORDINAL, MeasurementScale.INTERVAL, MeasurementScale.RATIO):
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        if n % 2 != 0:
            result["median"] = sorted_vals[n // 2]
        else:
            result["median"] = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2

    if variable.scale in (MeasurementScale.INTERVAL, MeasurementScale.RATIO):
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        result["mean"] = round(mean, 2)
        result["std_dev"] = round(variance ** 0.5, 2)
        result["min"] = min(values)
        result["max"] = max(values)

    return result


# Composite risk score
# Combines multiple vital sign classifications into one overall patient risk

@dataclass
class PatientRiskScore:
    patient_id: int
    bp_score: int = 0
    hr_score: int = 0
    temp_score: int = 0
    o2_score: int = 0
    preg_score: int = 0
    flags: List[str] = field(default_factory=list)

    @property
    def total_score(self):
        # BP is weighted more because it is the most critical in maternal care
        return (self.bp_score * 3) + (self.o2_score * 2) + self.hr_score + self.temp_score + self.preg_score

    @property
    def risk_category(self):
        if self.total_score >= 7:
            return "High"
        if self.total_score >= 3:
            return "Moderate"
        return "Low"


def compute_patient_risk_score(vital, preg_record=None):
    score = PatientRiskScore(patient_id=vital.patient_id if vital else 0)

    if vital:
        bp_cat = classify_blood_pressure(vital.blood_pressure_systolic)
        bp_map = {
            BPCategory.NORMAL: 0,
            BPCategory.ELEVATED: 1,
            BPCategory.HIGH: 2,
            BPCategory.CRITICAL: 3
        }
        if bp_cat:
            score.bp_score = bp_map[bp_cat]
            if bp_cat in (BPCategory.HIGH, BPCategory.CRITICAL):
                score.flags.append(f"BP {vital.blood_pressure_systolic}/{vital.blood_pressure_diastolic} mmHg is {bp_cat.value}")

        hr_cat = classify_heart_rate(vital.heart_rate)
        if hr_cat and hr_cat != HeartRateCategory.NORMAL:
            score.hr_score = 1
            score.flags.append(f"Heart rate {vital.heart_rate} bpm is {hr_cat.value}")

        temp_cat = classify_temperature(vital.temperature)
        if temp_cat and temp_cat != TemperatureCategory.NORMAL:
            score.temp_score = 1
            score.flags.append(f"Temperature {vital.temperature} degrees C is {temp_cat.value}")

        o2_cat = classify_oxygen_saturation(vital.oxygen_saturation)
        o2_map = {OxygenCategory.NORMAL: 0, OxygenCategory.LOW: 1, OxygenCategory.CRITICAL: 2}
        if o2_cat:
            score.o2_score = o2_map[o2_cat]
            if o2_cat != OxygenCategory.NORMAL:
                score.flags.append(f"SpO2 {vital.oxygen_saturation}% is {o2_cat.value}")

    if preg_record:
        score.preg_score = risk_level_to_int(preg_record.risk_level)
        if score.preg_score >= 1:
            score.flags.append(f"Pregnancy risk is {preg_record.risk_level}")

    return score


# Quick test when running the file directly
if __name__ == "__main__":

    class FakeVital:
        def __init__(self, pid, bp_sys, bp_dia, hr, temp, weight, rr, o2):
            self.patient_id = pid
            self.blood_pressure_systolic = bp_sys
            self.blood_pressure_diastolic = bp_dia
            self.heart_rate = hr
            self.temperature = temp
            self.weight = weight
            self.respiratory_rate = rr
            self.oxygen_saturation = o2

    class FakePreg:
        def __init__(self, pid, weeks, gravida, para, risk):
            self.patient_id = pid
            self.gestational_weeks = weeks
            self.gravida = gravida
            self.para = para
            self.risk_level = risk

    vitals = [
        FakeVital(1, 165, 105, 98,  37.2, 72.0, 18, 97),
        FakeVital(2, 118, 76,  72,  36.8, 65.5, 16, 98),
        FakeVital(3, 142, 92,  88,  38.4, 80.0, 20, 93),
        FakeVital(4, 110, 70, 110,  36.5, 58.0, 15, 99),
    ]

    pregnancies = [
        FakePreg(1, 34, 2, 1, "High"),
        FakePreg(2, 22, 1, 0, "Low"),
        FakePreg(3, 28, 3, 2, "High"),
    ]

    print("Validation results:")
    for v in vitals:
        errors = validate_vital_sign(v)
        if errors:
            print(f"  Patient {v.patient_id}: {len(errors)} issue(s)")
            for e in errors:
                print(f"    - {e.message}")
        else:
            print(f"  Patient {v.patient_id}: all values valid")

    print("\nClassification results:")
    for v in vitals:
        bp = classify_blood_pressure(v.blood_pressure_systolic)
        hr = classify_heart_rate(v.heart_rate)
        tmp = classify_temperature(v.temperature)
        o2 = classify_oxygen_saturation(v.oxygen_saturation)
        print(f"  Patient {v.patient_id}: BP={bp.value}  HR={hr.value}  Temp={tmp.value}  O2={o2.value}")

    print("\nRisk scores:")
    preg_map = {p.patient_id: p for p in pregnancies}
    for v in vitals:
        score = compute_patient_risk_score(v, preg_map.get(v.patient_id))
        print(f"  Patient {v.patient_id}: score={score.total_score}  risk={score.risk_category}")
        for flag in score.flags:
            print(f"    - {flag}")

    print("\nBP statistics:")
    stats = aggregate_vitals(vitals, "blood_pressure_systolic")
    for k, val in stats.items():
        print(f"  {k}: {val}")