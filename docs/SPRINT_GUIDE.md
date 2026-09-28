# Sprint Guide and the visual refresh

Sprint Guide is available from the floating chat button on every React page, including sign-in and recovery. Signed-in users can also open it from **Need a hand?** in the top bar.

Sprint Guide combines 23 documented workflow guides with a small set of live workspace tools. It is not a general-purpose AI chatbot. It uses the current user's authenticated SkillSprint APIs to retrieve records and can activate a selected document after explicit confirmation.

## Live requests

- “What is in the knowledge library?” returns actual document titles, IDs, versions, categories, status and effective dates. Up to 20 cards are shown from the API's latest 100 documents.
- “Read Security Policy” or **Read contents** fetches the selected document and displays up to five verbatim source excerpts with citation links. These are excerpts, not an AI-generated summary or a claim that the policy is approved. Quarantined content is not displayed as trusted guidance.
- “Activate Security Policy” prepares a choice of matching documents. **Review activation** shows the exact target and warns that an older version may be superseded and dependent plans marked stale. Only **Confirm activation** sends the change. The current document is re-read first to reject stale selections; the backend independently checks role, CSRF, quarantine and effective dates, and records its normal audit event.
- “Read it” resolves to the previous document only when there is one unambiguous target.
- “Show my plans” returns current plan titles and statuses within the user's scope. “Show workspace totals” reads the dashboard counts.
- Unknown actions are not executed. There is no arbitrary API, code execution, deletion, permission editing, or assessment-answer tool.

## Privacy and scope

- Messages stay in browser memory. They are not sent to the backend or an external AI service, written to local storage, or included in analytics by this feature.
- The conversation clears on refresh, sign-out, or account change. At most 20 exchanges are kept.
- Document reads and activation use the existing authenticated first-party API; message text and source content are not sent to an external AI provider. The only supported mutation is confirmed document activation.
- Guide visibility follows the current account role. Existing route and backend authorization remain authoritative.
- External AI conversation requires separate approval for sending message content to the selected provider; no such integration is enabled here.

## Maintenance

Update `frontend/src/lib/assistantGuides.ts` whenever workflows or permissions change. The allowlisted live tools are in `frontend/src/lib/assistantTools.ts`; their executable checks are in `frontend/scripts/check-assistant-tools.mjs`. Keep routes aligned with `App.tsx` and steps aligned with actual controls. Library list/detail screens refresh after an assistant activation succeeds.

The vector brand mark is `frontend/src/assets/skillsprint-mark.svg`. `BrandLogo` reuses it in the sidebar and login page; Vite fingerprints the same asset for the favicon. Shared colors, dashboard treatment, headers, buttons, cards and responsive spacing live in the existing frontend components and stylesheet.

## Verify and deploy

From `frontend`, run `npm run test:assistant`, `npm run test:navigation`, and `npm run build`. Backend authorization coverage lives in `tests/test_assistant_tools.py` (run against an isolated local test schema). Browser-check live library reads, source excerpts, activation cancel/confirm, chat open/close, keyboard Escape, suggested questions, page guidance, link navigation, clear conversation, and account switching at desktop and phone widths.

Deploy the updated frontend build to Vercel using the existing configuration. Also redeploy Railway for the activation response fix: HTTP 204 now has an empty body, avoiding a protocol error after successful activation. No new environment variables, API keys or database migrations are required. This change does not itself deploy the site.
