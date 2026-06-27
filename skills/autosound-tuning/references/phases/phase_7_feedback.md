# Phase 7 — Project Wrap-Up & Feedback

This phase closes the active tuning session, records findings, and feeds valuable generalizable lessons back into the parent skill repository.

## Core Objectives
1. **Log Session State:** Write the finalized tuning step into the session log and update the `tuning-changelog`.
2. **Execute the Closing Ritual:** Conduct the 4-stream feedback process with the user.
3. **Contribute to Community Knowledge:** Back up configurations and check for generalizable skill candidates.

---

## Step-by-Step Runbook

For complete instructions and templates, refer to [feedback-loop.md](file:///skills/autosound-tuning/references/feedback-loop.md).

### 1. Finalize Project Documentation & State
* Update `dsp-state-current` to reflect the exact crossover points, delays, gains, polarities, and virtual EQ shelves currently loaded into the vehicle's DSP.
* Append the final accepted configuration status to the `tuning-changelog`.
* Write a clean **▶️ CONTINUE** block at the top of the changelog reflecting that the session is complete, detailing any known acoustic limitations or hardware bugs remaining in the car (the backlog).

### 2. The 4-Stream Feedback Ritual
Proactively run the following four streams in interactive dialogue with the Arbiter:

* **Stream A: Project-Level Feedback**
  Collect a final review of the sonic results, discussing overall soundstage, spectral balance, and system enjoyment compared to baseline.
* **Stream B: Skill-Specific Feedback**
  Gather feedback specifically regarding **only the reference files and guidelines used during this session** (e.g., Was the Hashimoto guide helpful? Were the Helix phase instructions clear?). This helps identify which specific parts of the skill need refinement.
* **Stream C: Consent to Share**
  Request explicit permission to share the finalized car profile (`autosound_context.md`), frequency response curves, and tuning choices with the community.
  > [!IMPORTANT]
  > Ensure all personal data, geographical data, and raw measurements are stripped out before sharing. The user must manually upload/submit the file; the AI never transmits data automatically.
* **Stream D: Creator Support (Post-Submit Only)**
  If the session was highly successful and the user expresses satisfaction, share a quiet, non-obtrusive donation link.
  > [!CAUTION]
  > Never prompt or show the donation link as part of a form, questionnaire, or before the feedback streams are complete. Skip this step entirely if Sponsors is not configured.

### 3. Log Skill Candidates
* Scan the `tuning-changelog` and conversation history for any generalizable acoustic insights, new test tracks, or unique vehicle behavior discovered.
* Write any confirmed lessons into the local **Skill Inbox** (`rew_analitic/skill-inbox.md`), tagging them with `📚`.
* These candidate notes will be harvested, correlated, and folded back into the master skill repository during the next scheduled refactoring session.

---

## Technical Handoff
Ensure a final backup of the DSP binary config is saved under `rew_analitic/dsp-config/` with an updated `README.md` cataloging the file versions. The project workspace is now clean, documented, and officially complete!
