# Medium publishing notes

These are editorial notes, not part of the article. The article itself is in `TECHNICAL_BLOG.md`. It has not been published by this update.

## Suggested presentation

- **Title:** Building SkillSprint AI: An Onboarding App That Shows Its Evidence
- **Subtitle:** How React, FastAPI, PostgreSQL, and independent Python validation turn company documents into reviewable learning plans.
- **Suggested tags:** Artificial Intelligence, Python, React, Software Development, EdTech.
- **Short description:** A practical look at building source-grounded onboarding with independent validation, human review, policy updates, and lessons from a Railway/Vercel deployment.

## Prepare the story

Use the article's first line as the title and the following sentence as the subtitle; do not repeat them in the story body. Begin the body with “A generated onboarding plan can sound convincing…” Keep the section headings, short paragraphs, and opening pull quote. Check the rendered formatting after transferring the Markdown rather than assuming raw Markdown will render automatically.

Keep the final AI-assistance and fictional-data disclosure. Read the article yourself, correct anything that does not reflect your work, and use your actual author name. Do not invent a repository link, participant verification, or publication date.

## Optional screenshots and captions

Use fresh screenshots from the final version with fictional data:

1. After the introduction: the Overview screen. Caption: “SkillSprint AI brings company knowledge, role requirements, and learning plans into one workspace.”
2. After the role-matrix section: an approved requirement and its source evidence. Caption: “The approved requirement matrix supplies the expected obligations before generation begins.”
3. After the validation section: coverage and review findings. Caption: “Coverage and traceability checks support review; they do not replace a human assessment of meaning.”
4. After the learning section: a learner's modules and progress. Caption: “Learning completion is tracked separately from plan approval.”

Add descriptive alt text to any images you use. Do not publish broken-page screenshots as if they show the final UI. If illustrating a bug, label it explicitly as a before-fix example.

## Before publishing

- Deploy the latest frontend fixes and verify the authenticated workflow before describing the live version as current.
- Remove real employee information, emails, tokens, passwords, and configuration values from every screenshot. Do not use the previously shared Railway credentials screenshot. Revoke any credential already exposed.
- Verify public demo/repository links and decide whether you want to include them. Never publish administrator credentials for readers to try the app.
- Preserve the distinction between the 80-test full run and the overlapping five-test focused run. Do not add them together as 85 unique tests.
- Preserve the historical-performance caveat: the earlier benchmark is not a current PostgreSQL/Railway benchmark.
- Preview the title, headings, images, and links on both a narrow and wide screen.

The old submission ZIP and SHA256 manifest have not been regenerated. They should not be presented as containing this revised article until the submission package is rebuilt.
