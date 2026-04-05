# Real-World Vendor Contract Review - Complete Runbook

This runbook demonstrates a complete, realistic workflow using ONLY actual myna CLI commands. It covers: running a pipeline, monitoring execution, creating checkpoints, handling HITL approvals, and rolling back if needed.

---

## Complete Workflow Example

### Phase 1: Run the Pipeline

```bash
myna run ./pipelines/document_review.yml
```

**Output:**
```
SessionID: sess-f1a2b3c4-d5e6-f7g8-h9i0-j1k2l3m4n5o6
Status: RUNNING
Pipeline: document_review
Started: 2026-04-05T14:15:30Z
Input: ./tests/fixtures/sample_vendor_contract.pdf
```

**Save this Session ID.** You'll use it for all subsequent commands:
```bash
SESSION_ID="sess-f1a2b3c4-d5e6-f7g8-h9i0-j1k2l3m4n5o6"
```

---

## Phase 2: Monitor Execution

### Check Status in Real-Time
```bash
myna status $SESSION_ID
```

**Output (Step 1 - Summarization):**
```
Session: sess-f1a2b3c4-d5e6-f7g8-h9i0-j1k2l3m4n5o6
Status: RUNNING
Current Step: summarization_step
Progress: 0/3
Elapsed: 5.2s
Estimated Time Remaining: 45s
```

Re-run this command to watch progress:
```bash
myna status $SESSION_ID
```

**Output (Step 2 - Validation):**
```
Session: sess-f1a2b3c4-d5e6-f7g8-h9i0-j1k2l3m4n5o6
Status: RUNNING
Current Step: validation_step
Progress: 1/3
Elapsed: 21.4s
Estimated Time Remaining: 30s
```

**Output (Step 3 - Report Generation):**
```
Session: sess-f1a2b3c4-d5e6-f7g8-h9i0-j1k2l3m4n5o6
Status: RUNNING
Current Step: report_generation
Progress: 2/3
Elapsed: 38.6s
Estimated Time Remaining: 12s
```

### View the Audit Trail
At any time, view what's happened:
```bash
myna audit $SESSION_ID
```

**Sample Output (in progress):**
```
2026-04-05T14:15:30.123Z [summarization_step_started] file_summarizer skill invoked
2026-04-05T14:15:32.456Z [skill_invoked] skill_id: file_summarizer, model: gpt-4-turbo
2026-04-05T14:15:45.789Z [summarization_step_completed] extracted 5 key terms, confidence: 0.91
2026-04-05T14:15:46.012Z [policy_checked] policy_id: org.pii_block, result: NOT_TRIGGERED
2026-04-05T14:15:50.345Z [validation_step_started] data_validator skill invoked
2026-04-05T14:15:58.678Z [validation_step_completed] found 3 violations: GDPR_DATA_RETENTION(HIGH), SOC2_ACCESS_CONTROL(MEDIUM), GDPR_DATA_PROCESSING(HIGH)
2026-04-05T14:16:02.901Z [report_generation_step_started] report_writer skill invoked
2026-04-05T14:16:15.234Z [report_generation_step_completed] compliance_score: 68, risk_level: HIGH
2026-04-05T14:16:16.567Z [on_complete_write_audit_summary] audit summary archived
2026-04-05T14:16:17.890Z [on_complete_archive_session] session archived
2026-04-05T14:16:17.950Z [session_completed] Status: COMPLETED
```

---

## Phase 3: Create a Checkpoint (Optional)

If you want to save the current state:
```bash
myna checkpoint $SESSION_ID --label "after_validation"
```

**Output:**
```
Checkpoint created for session: sess-f1a2b3c4-d5e6-f7g8-h9i0-j1k2l3m4n5o6
Label: after_validation
Timestamp: 2026-04-05T14:15:58.678Z
Step: validation_step
```

You can create multiple checkpoints:
```bash
myna checkpoint $SESSION_ID --label "pre_report_generation"
```

---

## Phase 4: Session Completes

Check final status:
```bash
myna status $SESSION_ID
```

**Output:**
```
Session: sess-f1a2b3c4-d5e6-f7g8-h9i0-j1k2l3m4n5o6
Status: COMPLETED
Progress: 3/3
Duration: 47.8s
Result: SUCCESS
```

View complete audit trail:
```bash
myna audit $SESSION_ID
```

---

## Phase 5: Human-In-The-Loop (HITL) Approval Scenario

When a pipeline step requires manual approval, it pauses and creates a request.

### Scenario: Legal Review Required

Pipeline runs and creates a HITL request:
```bash
myna status $SESSION_ID
```

**Output:**
```
Session: sess-f1a2b3c4-d5e6-f7g8-h9i0-j1k2l3m4n5o6
Status: AWAITING_APPROVAL
Current Step: report_generation
Approval Request ID: hitl-req-9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d
Request Type: MANUAL_REVIEW
Message: "Compliance report generated. Please review violations and recommend action."
```

View the audit trail to see the report:
```bash
myna audit $SESSION_ID
```

Look for the `report_generation_step_completed` event containing the compliance report:
```
2026-04-05T14:16:15.234Z [report_generation_step_completed] 
  compliance_score: 68
  violations_found: [
    {type: GDPR_DATA_RETENTION, severity: HIGH, description: "Contract lacks explicit data retention policy"},
    {type: SOC2_ACCESS_CONTROL, severity: MEDIUM, description: "Missing SOC2 Type II access control requirements"},
    {type: GDPR_DATA_PROCESSING, severity: HIGH, description: "No Data Processing Agreement (DPA) clause found"}
  ]
  risk_level: HIGH
  remediation_required: true
```

### Approve the Request

After legal team reviews and approves:
```bash
myna approve $SESSION_ID --request-id hitl-req-9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d
```

**Output:**
```
Request approved for session: sess-f1a2b3c4-d5e6-f7g8-h9i0-j1k2l3m4n5o6
Request ID: hitl-req-9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d
Decision: APPROVED
Timestamp: 2026-04-05T14:18:30.123Z

Session will continue execution.
```

Check status again:
```bash
myna status $SESSION_ID
```

**Output:**
```
Session: sess-f1a2b3c4-d5e6-f7g8-h9i0-j1k2l3m4n5o6
Status: COMPLETED
Progress: 3/3
Duration: 120.4s
Result: SUCCESS
```

### Deny the Request (Rollback)

If the legal team rejects:
```bash
myna deny $SESSION_ID --request-id hitl-req-9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d
```

**Output:**
```
Request denied for session: sess-f1a2b3c4-d5e6-f7g8-h9i0-j1k2l3m4n5o6
Request ID: hitl-req-9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d
Decision: DENIED
Timestamp: 2026-04-05T14:18:45.567Z

Session will be rolled back.
```

---

## Phase 6: Rollback to Checkpoint

If you need to redo steps, rollback to a previous checkpoint:

### View Available Checkpoints

Check the audit trail for saved checkpoints:
```bash
myna audit $SESSION_ID
```

Look for `checkpoint_created` events:
```
2026-04-05T14:15:58.678Z [checkpoint_created] label: after_validation, step: validation_step
2026-04-05T14:16:02.901Z [checkpoint_created] label: pre_report_generation, step: report_generation
```

### Rollback to a Checkpoint

```bash
myna rollback $SESSION_ID --to after_validation
```

**Output:**
```
Rollback initiated for session: sess-f1a2b3c4-d5e6-f7g8-h9i0-j1k2l3m4n5o6
Target Checkpoint: after_validation
Target Step: validation_step

Rolling back from: report_generation
Files archived: report_generation.output, on_complete_hooks.status
State restored: validation_step.output

Session is now paused at checkpoint: after_validation
Use: myna resume <session_id> to continue from this point.
```

### Resume After Rollback

```bash
myna resume $SESSION_ID
```

**Output:**
```
Session resumed: sess-f1a2b3c4-d5e6-f7g8-h9i0-j1k2l3m4n5o6
Resuming from: validation_step
Next step: report_generation
Status: RUNNING
```

Check status:
```bash
myna status $SESSION_ID
```

**Output:**
```
Session: sess-f1a2b3c4-d5e6-f7g8-h9i0-j1k2l3m4n5o6
Status: RUNNING
Current Step: report_generation
Progress: 2/3
Elapsed: 12.3s
Estimated Time Remaining: 15s
```

---

## Phase 7: Pause and Resume During Execution

If you need to pause the pipeline mid-execution:

```bash
myna pause $SESSION_ID
```

**Output:**
```
Session paused: sess-f1a2b3c4-d5e6-f7g8-h9i0-j1k2l3m4n5o6
Paused at: validation_step
Timestamp: 2026-04-05T14:16:00.123Z
Status: PAUSED
```

Check status:
```bash
myna status $SESSION_ID
```

**Output:**
```
Session: sess-f1a2b3c4-d5e6-f7g8-h9i0-j1k2l3m4n5o6
Status: PAUSED
Current Step: validation_step (paused)
```

Resume:
```bash
myna resume $SESSION_ID
```

**Output:**
```
Session resumed: sess-f1a2b3c4-d5e6-f7g8-h9i0-j1k2l3m4n5o6
Resuming from: validation_step (from pause point)
Status: RUNNING
```

---

## Phase 8: Terminate a Session

If something goes wrong and you need to stop completely:

```bash
myna terminate $SESSION_ID
```

**Output:**
```
Session terminated: sess-f1a2b3c4-d5e6-f7g8-h9i0-j1k2l3m4n5o6
Timestamp: 2026-04-05T14:16:30.456Z
Status: TERMINATED
Last Step Completed: validation_step
Reason: User termination
```

Check status:
```bash
myna status $SESSION_ID
```

**Output:**
```
Session: sess-f1a2b3c4-d5e6-f7g8-h9i0-j1k2l3m4n5o6
Status: TERMINATED
Duration: 45.2s
Last Step: validation_step
```

---

## What a PASSING Run Looks Like

```bash
# 1. Start pipeline
$ myna run ./pipelines/document_review.yml
SessionID: sess-f1a2b3c4-d5e6-f7g8-h9i0-j1k2l3m4n5o6
Status: RUNNING

# 2. Check progress
$ myna status sess-f1a2b3c4-d5e6-f7g8-h9i0-j1k2l3m4n5o6
Status: RUNNING
Current Step: summarization_step

# ... wait for completion ...

# 3. Final status
$ myna status sess-f1a2b3c4-d5e6-f7g8-h9i0-j1k2l3m4n5o6
Status: COMPLETED
Progress: 3/3
Result: SUCCESS

# 4. View results
$ myna audit sess-f1a2b3c4-d5e6-f7g8-h9i0-j1k2l3m4n5o6
[... audit trail showing all steps completed ...]
[... report_generation_step_completed with compliance_score: 68 ...]
[... risk_level: HIGH, remediation_required: true ...]
[... on_complete_write_audit_summary ...]
[... on_complete_archive_session ...]
```

**PASS Criteria Met:**
- ✅ Session Status: COMPLETED
- ✅ All 3 pipeline steps executed (summarization, validation, report_generation)
- ✅ Compliance report generated with score >= 65
- ✅ All expected violations found (3 violations identified)
- ✅ Risk level: HIGH
- ✅ No unexpected policy triggers
- ✅ Audit trail complete with all checkpoint/hook events

---

## What a FAILING Run Looks Like

```bash
# 1. Start pipeline
$ myna run ./pipelines/document_review.yml
SessionID: sess-a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
Status: RUNNING

# 2. Check progress
$ myna status sess-a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
Status: ERROR
Error: "validation_step failed: Could not identify expected violations"
Timestamp: 2026-04-05T14:16:15.234Z

# 3. View audit to debug
$ myna audit sess-a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
[... summarization_step_completed ...]
[... validation_step_started ...]
[... validation_error: "Only 1 violation found, expected 3" ...]
[... session_failed ...]
```

**FAIL Criteria Present:**
- ❌ Session Status: ERROR (not COMPLETED)
- ❌ Validation step failed (not all violations identified)
- ❌ Pipeline did not reach report_generation step
- ❌ No compliance report generated

**Recovery:**
```bash
# Fix the test document or pipeline configuration, then run again:
myna run ./pipelines/document_review.yml
```

---

## Summary of Real Myna Commands Used

| Command | Purpose |
|---------|---------|
| `myna run ./pipelines/document_review.yml` | Start the pipeline |
| `myna status <session_id>` | Check current progress |
| `myna audit <session_id>` | View audit trail and events |
| `myna checkpoint <session_id> --label <name>` | Save a checkpoint |
| `myna rollback <session_id> --to <label>` | Rollback to checkpoint |
| `myna pause <session_id>` | Pause execution |
| `myna resume <session_id>` | Resume from pause or checkpoint |
| `myna terminate <session_id>` | Stop the session |
| `myna approve <session_id> --request-id <id>` | Approve HITL request |
| `myna deny <session_id> --request-id <id>` | Reject HITL request |
