# 2024 Constrained Chronology Reconciliation

Phase 3.5A preserves the 77-attempt corrected canonical backbone and adds only constraints supported by the supplied evidence pack, its cited source identities, and compatible Timing71 captures. The count comprises 74 official Results attempts plus three preserved `C_SECTION_ONLY` evidence rows from the preceding correctness patch. Capture, editorial anchor, and timed-run endpoint semantics remain separate.

## Outcome

| Metric | Result |
|---|---:|
| Canonical attempts | 77 |
| Timing71 capture events | 97 |
| Uniquely linked captures | 8 |
| Ambiguous or unlinked captures | 89 |
| Approximate observed attempt constraints | 4 |
| Bounded attempt constraints | 4 |
| Ordering-only attempt constraints | 1 |
| Unknown attempt constraints | 68 |
| Deterministic duration values | 71 |
| Complete four-lap duration values | 54 |
| Partial observed-duration constraints | 17 |
| Bounded timed-run endpoint constraints | 2 |
| Usable inter-attempt-gap diagnostics | 0 |

2024 chronology reconciliation remains **PARTIAL**. The global gate is unchanged.

## Golden cases

- VeeKay multi-anchor sequence: **PASS**.
- Rahal final-attempt consistency: **PASS**.

VeeKay's four canonical attempts are ordered as crash, 3:26 p.m. waved-off run, approximately 3:51 p.m. 231.166 mph run, and the final 232.419 mph run. The final run has a bounded finish of 21:49:50-21:50:00 UTC and a duration-derived bounded start of 21:47:15.107-21:47:25.107 UTC. Rahal's final track entry is bounded after VeeKay and no later than the cutoff; it is not represented as release time or timed-run start.

## Timing71 reconciliation

Eight captures are linked: four VeeKay anchors, two Rossi anchors, Power's independently ordered initial run, and Rahal's externally documented final-attempt context. The remaining 89 captures are unlinked. Every link requires an independent anchor plus compatible car identity, attempt structure, and sequence; no link uses positional order alone.

## Contradiction assessment

No hard contradiction exists among the eight accepted links after capture semantics are kept separate. The following conflicts prevent broader linkage:

- Larson's available car 17 capture sequence is incompatible with the cited sixth-initial-order fact if capture time is interpreted as on-track order, so no Larson capture is linked.
- Rahal's final recorder capture is 26 seconds after the official cutoff, while the article places track entry just before the cutoff. This confirms that capture time cannot be treated as release or track-entry time.
- VeeKay's first capture follows the reported crash minute. It is linked only as a capture associated with the uniquely identified attempt and is not converted into timed-run start.

## Evidence and uncertainty

The supplied DOCX is registered as a secondary compilation. Each used anchor retains the cited underlying source identity. Official INDYCAR editorial evidence ranks ahead of NBC and Motorsport.com editorial evidence; the pack itself does not supersede those sources.

Event-time quality describes precision. Field-level provenance separately records whether a value is reconstructed from official evidence, inferred uncertainly from editorial evidence, or deterministically derived. The bounded VeeKay start inherits the bounded finish uncertainty despite exact duration arithmetic.

No queue-entry time, release time, queue wait, lane chronology, queue length, queue position, or full historical queue state is materialized. No inter-attempt gap meets the required paired timed-run-boundary standard in this phase.

## Sources

- [Official INDYCAR qualifying explainer](https://www.indycar.com/-/media/Files/2024/NICS/06-500/indycar-qual-explainer-2024Indy500.pdf)
- [Official INDYCAR VeeKay Paddock Buzz](https://www.indycar.com/news/2024/05/05-18-buzz)
- [Official INDYCAR Day 1 report](https://www.indycar.com/News/2024/05/05-18-Quals-Day1)
- [NBC Sports live qualifying blog](https://www.nbcsports.com/motor-sports/news/indy-500-live-qualifying-blog-updates-day-1-problem-kyle-larson-rinus-veekay)
- [Motorsport.com Day 1 report](https://www.motorsport.com/indycar/news/indy-500-penske-heroic-veekay-rebounds-crash/10612685/)

## Baseline comparison

Pre-Phase-3.5A: **97 Timing71 capture events / 0 linked 2024 attempts**.
Post-Phase-3.5A: **97 Timing71 capture events / 8 uniquely linked captures / 89 unresolved captures**.
