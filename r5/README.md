# R5 corrected physics-first architecture

R5 is an additive research branch. It supersedes the R4F7/F8G/F8H performance
mechanism for future simulator use without modifying or deleting any frozen R3
or R4 artifact.

The operational chain is:

`current result + current observable physical state + action wait -> future time
-> decision-time-forecast future physical state -> same-car speed change
distribution -> retain/withdraw result semantics`.

The primary response model is trained on consecutive, same-car Day 1 attempts.
It uses only PTSC observations already available at each attempt and HRRR cycles
available under the frozen 90-minute availability policy. Fast Friday appears
only as a legacy ablation. PTSC track surface temperature is never replaced by
ambient air temperature. Solar geometry is deterministic astronomy; no corner
shadow, tyre temperature, tyre pressure, rubbering, or grip truth is created.

Run `python3 r5/run_r5_corrected_physics_pipeline_v1.py` from the repository
root. All generated artifacts are written to `r5/output/` with deterministic
ordering, seeds, and SHA256 hashes.

