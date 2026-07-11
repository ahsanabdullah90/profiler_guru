# Clinical & Compliance Roadmap

This document tracks planned compliance improvements, professional boundary safeguards, and scalability enhancements for multi-practitioner production environments.

---

## 1. Professional Boundaries & Off-Hours Crisis Safeguards
- **Audit Finding:** The WhatsApp integration lacks explicit out-of-office or crisis-routing boundaries.
- **Clinical Impact:** Clients sending distress messages off-hours during therapist offline windows, creating potential liability and therapeutic frame breaches.
- **Proposed Solution:** Implement an out-of-office configuration screen where clinicians define local office hours and crisis message templates. If messages are ingested during off-hours, the bridge listener will send an automated reply recommending local emergency resources (e.g. calling/texting 988 in the US).

## 2. Configurable Patient Record Retention Locks
- **Audit Finding:** Patient records are subject to immediate global purge actions.
- **Clinical Impact:** Risk of destroying patient files that are legally required to be preserved (e.g., pediatric psychiatric records must be kept for 7+ years in many jurisdictions).
- **Proposed Solution:** Add a `retention_lock_until` field to patient profiles. Any cascade delete or purge operation must be gated to check if the current date is past the retention lock. If not, the delete is blocked and clinician overrides require dual-factor authorization.

## 3. Practitioner Roles & Supervisory Workflows (RBAC)
- **Audit Finding:** Trainee therapists can finalize clinical assessments and notes without supervisors co-signing.
- **Clinical Impact:** Practice compliance risk where unlicensed trainee entries are not signed off by a licensed clinical supervisor.
- **Proposed Solution:** Introduce role-based access control (RBAC) with supervisor, trainee, and admin roles. Trainee note entries will go into a `pending_signature` state and will not appear in the official patient record export until a supervisor co-signs the entry.
