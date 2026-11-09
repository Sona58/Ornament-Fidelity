#!/usr/bin/env python
"""OPTIONAL reference check of Module 1: CV-quantum expectation trajectories (PennyLane
`default.gaussian`) vs the closed-form classical trajectories used in models.py.

NOTE: this is a minimal reference implementation written for the repo. If your original
manuscript code differs (e.g. in how rotation is applied), replace this file with your
original so the published equivalence result matches the paper exactly.

Convention (PennyLane, hbar = 2):  <x> = 2 Re(alpha) after Displacement(alpha, 0).
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pennylane as qml  # noqa: E402

dev = qml.device("default.gaussian", wires=1)


@qml.qnode(dev)
def displaced(a):
    qml.Displacement(a, 0.0, wires=0)
    return qml.expval(qml.QuadX(0))


@qml.qnode(dev)
def displaced_rotated(a, theta):
    qml.Displacement(a, 0.0, wires=0)
    qml.Rotation(theta, wires=0)
    return qml.expval(qml.QuadX(0))


@qml.qnode(dev)
def disp_rot_disp(a_osc, theta, b_centre):
    """D(b) R(theta) D(a)|0>:  <x> = 2 [ b + a cos(theta) ]  -> centre(t) + A cos(theta(t))."""
    qml.Displacement(a_osc, 0.0, wires=0)
    qml.Rotation(theta, wires=0)
    qml.Displacement(b_centre, 0.0, wires=0)
    return qml.expval(qml.QuadX(0))


def main():
    t = np.linspace(0, 1, 201)
    start, end, scale = 0.0, 300.0, 100.0            # cents; cents per unit of <x>
    # Meend: cosine-eased path, realised as a time-dependent displacement
    path = start + (end - start) * (1 - np.cos(np.pi * t)) / 2
    q = np.array([displaced(float(p / scale / 2.0)) * scale for p in path])
    c = path
    d1 = np.max(np.abs(q - c))
    # Andolan: displaced state (centre) then phase-space rotation sweeping linearly
    centre, amp, f, T = 0.0, 40.0, 3.0, 2.0
    tt = np.linspace(0, T, 401)
    a0 = amp / scale / 2.0
    q2 = np.array([displaced_rotated(a0, 2 * np.pi * f * x) * scale + centre for x in tt])
    c2 = centre + amp * np.cos(2 * np.pi * f * tt)
    d2 = np.max(np.abs(q2 - c2))
    # Meend, extended (Module 1+): hold - linear ramp - hold, i.e. a displacement whose path alpha(t) is
    # piecewise linear (the best-fitting glide model on Saraga). Any path is realisable the same way.
    ramp = np.clip((t - 0.25) / 0.5, 0, 1)
    path_pl = -100 + 400 * ramp
    q3 = np.array([displaced(float(p / scale / 2.0)) * scale for p in path_pl])
    d3 = np.max(np.abs(q3 - path_pl))
    # Andolan + drift (Module 1+): centre drifts linearly while the oscillation rotates
    drift = 60.0 * tt / T
    q4 = np.array([disp_rot_disp(a0, 2 * np.pi * f * x, float(dr / scale / 2.0)) * scale
                   for x, dr in zip(tt, drift)])
    c4 = drift + amp * np.cos(2 * np.pi * f * tt)
    d4 = np.max(np.abs(q4 - c4))
    print(f"Meend  : max |quantum - classical| = {d1:.3e} cents")
    print(f"Andolan: max |quantum - classical| = {d2:.3e} cents")
    print(f"Meend, plateau-ramp path (Module 1+)      : {d3:.3e} cents")
    print(f"Andolan + linear drift (Module 1+)        : {d4:.3e} cents")
    print("All ~ machine precision" if max(d1, d2, d3, d4) < 1e-9 else "WARNING: non-negligible difference")


if __name__ == "__main__":
    main()
