# R5.1 physics evidence data assembly

R5.1 assembles auditable evidence tables only. It does not fit or select a
performance model, estimate a wait distribution, run a strategy simulator, or
recommend RETAIN/WITHDRAW/REATTEMPT actions.

The assembly keeps Day 1 and Last Chance sources separate. Fast Friday records
are exposed as per-car, per-year candidate evidence; existing repository
selections are preserved without creating a new selection rule. General fastest
laps and no-tow single laps are not relabelled as four-lap qualifying averages.

Run from the repository root:

```bash
python3 r5_1/run_r5_1_data_assembly_v1.py
```

The script reads protected inputs and writes only to `r5_1/output/`.

