"""
Grading core: takes a learner-built circuit + their predicted outcome
distribution, runs it on AerSimulator, and checks the prediction against
the actual measured distribution within a per-challenge tolerance band.

This is the one place "did the learner get it right" is decided. The
frontend never computes correctness — it only renders what this returns.
"""
from dataclasses import dataclass
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

SHOTS = 4096


@dataclass
class GateOp:
    gate: str          # "h" | "x" | "z" | "cx" | ...
    qubits: list[int]


@dataclass
class GradeResult:
    measured_distribution: dict[str, float]   # e.g. {"00": 0.49, "11": 0.51}
    prediction: dict[str, float]
    correct: bool
    per_outcome_deltas: dict[str, float]


def build_circuit(num_qubits: int, ops: list[GateOp]) -> QuantumCircuit:
    qc = QuantumCircuit(num_qubits, num_qubits)
    for op in ops:
        getattr(qc, op.gate)(*op.qubits)
    qc.measure(range(num_qubits), range(num_qubits))
    return qc


def simulate(qc: QuantumCircuit) -> dict[str, float]:
    backend = AerSimulator()
    transpiled = transpile(qc, backend)
    result = backend.run(transpiled, shots=SHOTS).result()
    counts = result.get_counts()
    return {outcome: count / SHOTS for outcome, count in counts.items()}


def grade(
    num_qubits: int,
    ops: list[GateOp],
    prediction: dict[str, float],
    tolerance_low: float,
    tolerance_high: float,
) -> GradeResult:
    """
    tolerance is applied per-outcome around the LEARNER'S predicted value —
    e.g. a 0.50 prediction with a 0.45–0.55 band on that topic's config.
    Every predicted outcome must fall within its own measured value's band
    to count as correct; this rewards understanding the distribution shape,
    not just guessing one bucket right.
    """
    qc = build_circuit(num_qubits, ops)
    measured = simulate(qc)

    deltas = {}
    all_within = True
    for outcome, predicted_p in prediction.items():
        measured_p = measured.get(outcome, 0.0)
        deltas[outcome] = round(measured_p - predicted_p, 4)
        # tolerance band is defined on the measured value, learner must land inside it
        if not (tolerance_low <= predicted_p <= tolerance_high) and abs(measured_p - predicted_p) > (tolerance_high - tolerance_low) / 2:
            all_within = False

    return GradeResult(
        measured_distribution=measured,
        prediction=prediction,
        correct=all_within,
        per_outcome_deltas=deltas,
    )
