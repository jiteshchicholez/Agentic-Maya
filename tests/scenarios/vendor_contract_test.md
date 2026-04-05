# Vendor Contract Compliance Review - Test Execution Guide

## Overview
This guide walks through executing the vendor contract compliance review scenario against the `document_review` pipeline. The test validates that the system correctly identifies GDPR and SOC2 violations in vendor contracts and produces a compliance report.

## Prerequisites
- Myna framework installed and configured
- `pipelines/document_review.yml` exists
- Test fixture: `tests/fixtures/sample_vendor_contract.pdf` available
- Terminal with myna CLI access

---

## Step-by-Step Execution

### Step 1: Prepare the Test Document
Create or place your sample vendor contract PDF in the fixtures directory:
```
tests/fixtures/sample_vendor_contract.pdf
```
This should be a realistic vendor agreement with known GDPR and SOC2 compliance gaps.

### Step 2: Start the Pipeline Run
Execute the document_review pipeline:
```bash
myna run ./pipelines/document_review.yml
```

**Expected Output:**
```
Session ID: sess-a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
Status: RUNNING
Started: 2026-04-05T14:15:30Z
```

**Save the Session ID for subsequent steps.**

### Step 3: Monitor Pipeline Execution
View the audit trail to watch progress:
```bash
myna audit sess-a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
```

**What to Look For (in audit output):**

1. **Summarization Phase (file_summarizer skill)**
   - Event: `summarization_step_started`
   - Extract: vendor_name, service_scope, data_responsibilities
   - Confidence scores >= 0.85
   - Event: `summarization_step_completed`

2. **Validation Phase (data_validator skill)**
   - Event: `validation_step_started`
   - Identify 3 violations:
     - GDPR_DATA_RETENTION (HIGH)
     - SOC2_ACCESS_CONTROL (MEDIUM)
     - GDPR_DATA_PROCESSING (HIGH)
   - Event: `pii_block_policy_checked` (should NOT trigger)
   - Event: `validation_step_completed`

3. **Report Generation Phase (report_writer skill)**
   - Event: `report_generation_step_started`
   - JSON report with:
     - `compliance_score`: 65-100 expected
     - `violations_found`: 3 violation objects
     - `risk_level`: HIGH
     - `remediation_required`: true
   - Event: `on_complete_write_audit_summary`
   - Event: `on_complete_archive_session`
   - Event: `report_generation_step_completed`

**Watch until:** Status shows `COMPLETED`

### Step 4: Check Session Status
Check current processing step:
```bash
myna status sess-a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
```

**Expected Output:**
```
Session: sess-a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
Status: COMPLETED
Current Step: report_generation
Duration: 45.2 seconds
```

### Step 5: Verify Audit Trail Integrity
Confirm all checkpoints are recorded:
```bash
myna audit sess-a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
```

**Must Verify:**
- ✅ `summarization_step_completed` event
- ✅ `validation_step_completed` event
- ✅ `report_generation_step_completed` event
- ✅ `on_complete_write_audit_summary` event
- ✅ `on_complete_archive_session` event

---

## PASS Criteria

All of the following must be true for the test to **PASS**:

### Pipeline Completion
```bash
myna status sess-a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
```
Expected: `Status: COMPLETED` (not ERROR, not TIMEOUT)

### Audit Trail Events Present
```bash
myna audit sess-a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
```
Must contain:
- ✅ `summarization_step_started`
- ✅ `summarization_step_completed`
- ✅ `validation_step_started`
- ✅ `validation_step_completed`
- ✅ `report_generation_step_started`
- ✅ `report_generation_step_completed`
- ✅ `on_complete_write_audit_summary`
- ✅ `on_complete_archive_session`

### Compliance Detection Accuracy
Report must identify:
- ✅ Exactly 3 violations (all expected violations found)
- ✅ GDPR_DATA_RETENTION marked as HIGH severity
- ✅ SOC2_ACCESS_CONTROL marked as MEDIUM severity
- ✅ GDPR_DATA_PROCESSING marked as HIGH severity

### Report Quality
```bash
# View full audit to extract report content
myna audit sess-a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
```
Must contain:
- ✅ `compliance_score` >= 65 (minimum acceptable)
- ✅ `risk_level`: "HIGH"
- ✅ `remediation_required`: true
- ✅ All required JSON fields present

### No Unexpected Policy Triggers
```bash
myna audit sess-a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
```
Must NOT contain:
- ✅ `pii_block_policy_triggered` (clean document, no PII)
- ✅ `budget_guard_policy_triggered` (within budget limits)
- ✅ `critical_escalation_triggered` (violations present but not CRITICAL)

---

## FAIL Criteria

The test **FAILS** if ANY of these occur:

### Pipeline Failed
```bash
myna status sess-a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
```
Returns: `Status: ERROR` or `Status: TERMINATED` or timeout > 300 seconds

### Missing Audit Events
```bash
myna audit sess-a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
```
Missing any of:
- ✅ `summarization_step_completed`
- ✅ `validation_step_completed`
- ✅ `report_generation_step_completed`

### Violations Incorrectly Detected
- ✅ Fewer than 3 violations found
- ✅ More than 3 violations found
- ✅ Violation severity incorrectly categorized

### Report Quality Issues
- ✅ `compliance_score` < 65
- ✅ `risk_level` is not "HIGH"
- ✅ Missing required JSON fields
- ✅ Invalid or incomplete report structure

### Unexpected Policy Triggers
```bash
myna audit sess-a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
```
Contains:
- ✅ `pii_block_policy_triggered` (false positive)
- ✅ `budget_guard_policy_triggered` (false positive)
- ✅ `critical_escalation_triggered` (false positive)

---

## Troubleshooting

### Pipeline Hangs or Timeout
Check status:
```bash
myna status sess-a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
```
If stuck, pause and resume:
```bash
myna pause sess-a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
myna resume sess-a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
```
If recovery fails, terminate:
```bash
myna terminate sess-a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
```

### Missing Violations in Report
Check audit trail for validation step details:
```bash
myna audit sess-a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
```
Look for: `validation_step_completed` entries showing violation count.
If low, test document may be missing expected violation patterns.

### Unexpected Policy Trigger
Review policy events in audit:
```bash
myna audit sess-a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
```
Look for `policy_triggered` events. Verify policy scope and conditions.

---

## Cleanup After Test

Terminate session if needed:
```bash
myna terminate sess-a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
```

Archive session for later analysis (save audit output):
```bash
myna audit sess-a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6 > test_results/session_audit.txt
```
