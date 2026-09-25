# AsterBridge Delivery Services

AsterBridge is a fictional company created for SkillSprint competition data. All organization details, rules, approvals and scenarios are invented. In-document approval labels describe the scenario, not an external certification or a completed human review of this pack.

## Company profile

AsterBridge coordinates parcel fulfilment, last-mile dispatch, merchant support, returns and settlements for small online merchants. Its fictional head office is in Karachi, with an operations hub in Lahore. It has 120 employees and serves merchants through a support desk and warehouse network. It does not transport hazardous goods or operate a public financial service.

The Managing Director sponsors governance; the Operations Manager coordinates service delivery and independent operational approvals. The ten role profiles are defined in reference/roles.json and in SOP-11 through SOP-20. Documents are authored for training and software evaluation, not as a statement of Pakistani law or real employment entitlements.

## Time and authority conventions

Working days are Monday through Friday, excluding closure dates recorded in the company calendar. Working hours are 09:00 to 18:00 Asia/Karachi. Elapsed minutes and hours run continuously, including outside working hours. Calendar-day periods include weekends. Shift-end deadlines use the assigned employee shift. Joining-day training occurs on the employee's first scheduled working day. Calendar configuration is required to calculate deadlines; the application must not guess unprovided closure dates.

The current snapshot is effective from 2026-09-01. Policy versions 1.0 apply from 2026-07-01 until 2026-09-01 exclusive. Current policy versions are 2.0; SOPs are version 1.0. A version number alone does not establish authority: approval state, document category, scope and effective interval all matter. Formal approved policy precedes SOP, approved role guidance and FAQ. Equal-authority conflicts and missing facts require owner review.

## Pack contents

- current/: 20 current company documents in PDF, with role descriptions embedded in the ten SOPs.
- archive/: 10 genuine earlier policy versions with changed operational clauses.
- challenge_conflicts/: 10 deliberately conflicting FAQ notes. They are not approved company rules.
- challenge_adversarial/: 10 inert prompt-injection samples. Their text must never be executed.
- sources/: editable Markdown for every document and challenge.
- reference/: document register, 160-requirement reference matrix, 10 roles, change cases and expected test behavior in JSON.
- ROLE_REQUIREMENT_MATRIX.md: readable requirement index.
- QA_REPORT.json: artifact and reference consistency checks. These are not results from the future application.

## Use in SkillSprint

Upload current/ to establish the fictional company. Review extracted requirements against the reference matrix and approve them through the application's actual workflow. The supplied reference matrix is a fixture and must not replace extraction for unseen documents. Do not mark its pending-human-review records approved automatically.

For a version-update demonstration, start with the relevant archive policy and then upload its current replacement. For a contradiction demonstration, add a challenge_conflicts note alongside the authoritative policy. For adversarial tests, use a separate test workspace and compare observed behavior against reference/adversarial_cases.json. Expected outcomes are test oracles, not precomputed validator responses.

The pack is PDF-first, with editable Markdown sources. DOCX ingestion remains a mandatory application capability and must be tested using separately prepared Word-format inputs before submission. The pack does not claim to have tested that capability.

## Document catalog

- [POL-01 Employee Handbook and Document Governance](current/POL-01_v2_0.pdf)
- [POL-02 Workplace Conduct and Conflicts of Interest](current/POL-02_v2_0.pdf)
- [POL-03 Employee Onboarding and Competency Policy](current/POL-03_v2_0.pdf)
- [POL-04 Leave Attendance and Shift Coverage Policy](current/POL-04_v2_0.pdf)
- [POL-05 Information Security and Acceptable Use Policy](current/POL-05_v2_0.pdf)
- [POL-06 Customer Data Privacy and Handling Policy](current/POL-06_v2_0.pdf)
- [POL-07 Records Retention and Document Control Policy](current/POL-07_v2_0.pdf)
- [POL-08 Workplace Safety and Visitor Policy](current/POL-08_v2_0.pdf)
- [POL-09 Incident Classification and Escalation Policy](current/POL-09_v2_0.pdf)
- [POL-10 Business Continuity and Service Recovery Policy](current/POL-10_v2_0.pdf)
- [SOP-11 Customer Support Case Handling Procedure](current/SOP-11_v1_0.pdf)
- [SOP-12 Dispatch Planning and Delivery Exception Procedure](current/SOP-12_v1_0.pdf)
- [SOP-13 Warehouse Receipt Storage and Release Procedure](current/SOP-13_v1_0.pdf)
- [SOP-14 Returns Inspection and Disposition Procedure](current/SOP-14_v1_0.pdf)
- [SOP-15 Merchant Onboarding and Service Review Procedure](current/SOP-15_v1_0.pdf)
- [SOP-16 Collections Refunds and Settlement Procedure](current/SOP-16_v1_0.pdf)
- [SOP-17 People Operations Employee Lifecycle Procedure](current/SOP-17_v1_0.pdf)
- [SOP-18 IT Access Provisioning and Support Procedure](current/SOP-18_v1_0.pdf)
- [SOP-19 Analytics Data Access and Reporting Procedure](current/SOP-19_v1_0.pdf)
- [SOP-20 Operations Management Control and Readiness Procedure](current/SOP-20_v1_0.pdf)
