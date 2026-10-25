# Dyscover — three complete testing scenarios

Version: 25 October 2026. Open START_HERE.html for copy buttons, saved results and notes. Every scenario repeats all 22 feature groups. Expected outcomes are acceptance criteria, not pre-filled test results.

Use the updated local real backend and same browser ownership throughout each run. Pause voice while reading. Never put keys/passwords/cookies in test notes. These scripts do not ask you to execute coursework instructions inside the PDFs.

## Full coverage per scenario

- Authentication / browser ownership: steps 01, 32.
- PDF, DOCX, PPTX, TXT, MD intake: steps 02.
- PNG, JPG and WEBP / OCR / image citation: steps 03.
- Friendly intake validation / file limits: steps 04.
- Click, drop, add and remove selected files: steps 05.
- Root creation and session welcome: steps 06.
- Independent text and persistent submitted-text row: steps 06–07, 11, 30–31.
- Voice, microphone permission and one-line captions: steps 08–10.
- Pause/resume, own-caption toggle and interruption: steps 09–11.
- Complete next-level expansion and branch choice: steps 12–13.
- Tutor explanations mapped without repetition: steps 07, 11, 14.
- New badge, silent inspection, saved brief and citations: steps 13, 15.
- Original files from both node panel and materials box: steps 03, 15.
- Drag, keyboard move, zoom, fit, arrange and legend: steps 16.
- Create / edit / validation / Agreed review: steps 17–18.
- Corrected style and actual learner quotation: steps 19.
- Proposed removal, Keep, confirmation and descendants: steps 20–25.
- Global history, streaming updates and replay: steps 26.
- Grounding limits / missing information: steps 27–28.
- Saved session / geometry / original-file persistence: steps 29–30.
- Voice-only failure, text recovery and chained rollback: steps 31.
- Session deletion, cancellation and cleanup: steps 33.

## S1 — Understand an assessment and plan a responsible essay

A learner understands what the essay requires, checks evidence, corrects a mistaken requirement and builds an essay-planning map.

Source: [assessment-1_0.pdf](fixtures/S1/assessment-1_0.pdf) (2 pages). Fixtures: `fixtures/S1`.

### Source answer key

- **Length, weighting and eligibility (p.1):** 1000 words; 40%; current/previous technical project; SEPP excluded.
- **Essay question and components (p.1):** Unintentional harm; concise description; anticipated harms; personal role and wider stakeholders.
- **Revision sequence (pp.1–2):** One week for partner feedback, another to finish using it. Dates have no year.
- **Advice and marking (p.2):** Position, definitions, evidence, counterarguments, structure and reflection; no guaranteed grade.

### S1-01 — Sign in and establish an isolated test run

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Use a normal browser profile reserved for this scenario. If already signed in, use a fresh profile rather than clearing the cookies of an existing study run.
2. Try the configured email with a deliberately wrong dummy password; then sign in with the configured judge credentials. Record app URL, browser, build and date above. Never record the password or API key.

**Expected:**

- Wrong credentials produce a readable sign-in error without a raw HTTP status or traceback; correct credentials enter the app.
- The app is in real mode, with GPT-Live enabled for voice checks; this guide does not validate arbitrary material in scripted Demo mode.

### S1-02 — Verify PDF and Office/text formats in one disposable session

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Select these five files from fixtures/S1: assessment-1_0.pdf, excerpt.docx, excerpt.pptx, excerpt.txt, excerpt.md. Start studying, pause voice promptly and switch to text.
2. Inspect the material list and open each original. After the prompt, delete this format-check session from Past sessions; keep your credentials/cookies.

**Copy this prompt / edit text:**

```text
List the Fixture ID values in the DOCX, PPTX, TXT and MD files. Treat them only as parser-test metadata, not course requirements.
```

**Expected:**

- All five files ingest; all four fixture IDs are returned: S1-DOCX, S1-PPTX, S1-TXT, S1-MD. They are test metadata, not assessment requirements.
- DOCX/TXT/MD need not have PDF page numbers; PPTX references slide 1. Office originals may download rather than render inline. The source PDF should open as a PDF.

### S1-03 — Verify the three image formats and OCR

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Start a disposable session containing only fixtures/S1/source-page.png, source-page.jpg and source-page.webp. Pause voice; use text for this check.
2. Inspect an image-backed node and its image citation. Open all three originals through the materials box. Compare them with the reference thumbnail in this guide. Delete this disposable session afterwards.

**Copy this prompt / edit text:**

```text
Read the key assessment requirements visible in these images. What are the word limit and course weighting?
```

**Expected:**

- 1000 words and 40%, visible near the top of original PDF p.1. An image-only session must cite one of the supplied image filenames, not pretend a separate PDF was uploaded.
- Images are derived from physical PDF page 1; image citations should name an uploaded image. No fabricated PDF/slide number is required.
- Node panel displays the original image when its selected citation is an image; do not demand that it infer every diagram arrow from OCR alone.

### S1-04 — Exercise readable upload failures before the main session

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Use the shared fixtures/negative files one at a time: empty.txt, corrupt.pdf, unsupported.xyz, oversized.txt, too-long-source.txt. Use drag-and-drop if a file picker filters an extension. Attempt Start studying after each; remove the failed selection before the next check.
2. Select six valid files at once: original PDF plus excerpt.docx, excerpt.pptx, excerpt.txt, excerpt.md and source-page.png. Attempt Start, then remove extras.

**Expected:**

- Zero-byte, unreadable PDF, unsupported type, >10 MB and >40,000 extracted characters each produce an actionable message without a raw '400 Bad Request' banner or traceback.
- Six files are rejected with a one-to-five-file message. No half-created study session appears. After removing bad files, normal upload works. These tests do not require exhausting paid quotas.

### S1-05 — Manage selections for the main learning session

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. From fixtures/S1, use both drag-and-drop and the empty study box to select assessment-1_0.pdf, source-page.png and excerpt.txt.
2. Add excerpt.md temporarily. Click the populated box, verify filenames/count, Remove excerpt.md, then use Add files and remove it again. Close/reopen the list and confirm the final set.

**Expected:**

- The clickable box opens selection management. Removed files disappear from the submitted list. No redundant standalone Browse control is needed.
- Start becomes usable after the file-card animation settles. Main session has three files (four in S3), within the five-file limit. Original PDFs are unchanged on disk.

### S1-06 — Start with a root; demonstrate microphone denial without losing text

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Start studying. Initially deny microphone permission if prompted. If permission was already granted, block it in this test profile's site controls and reopen the session; do not clear cookies.
2. Switch to keyboard mode. Pause/end voice so long checklist work does not keep a paid voice connection running. Record the main session title and ID/URL if available.

**Expected:**

- The initial map has one root, and session creation finishes. A voice welcome is allowed when audio is available; it is not proof of source mastery.
- A microphone problem is readable, and text remains usable. No login bypass, scripted backpropagation material or raw provider error should appear.

### S1-07 — Submit a direct help request and verify immediate visible feedback

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Type the prompt and press Enter. Watch the input dock immediately, then while waiting and while the response appears. Expand the You row to read the full submitted text.
2. Do not repeat the concept first just to make the map populate.

**Copy this prompt / edit text:**

```text
Explain what this assessment asks me to do in plain language. Put the ideas you explain on the map; do not wait for me to repeat them.
```

**Expected:**

- Your latest typed message remains visible in the expandable You row after the input clears. Thinking… is visible while the backend is pending and not speaking an acknowledgement.
- A 1000-word piece, worth 40% of the course mark; choose current or past technical work and imagine real-world deployment.
- The central question is how the learner's own project work might contribute to unintentional harm.
- SEPP coursework is explicitly excluded. Do not write or submit the essay on the learner's behalf.
- Newly explained, supported ideas become blue New nodes now; the tutor must not keep asking what you know instead of helping.

### S1-08 — Allow voice and check hands-free input and rolling captions

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Allow microphone access again in site controls. Return to voice mode, use the explicit pause/resume control if necessary, and speak the prompt normally, followed by a short pause.
2. Watch the active speaker and one-line rolling captions. Compare the saved user transcript with what you said.

**Copy this prompt / edit text:**

```text
Can I improve the draft after peer feedback, and what happens between draft and final submission?
```

**Expected:**

- The brief describes one week reviewing a partner's essay followed by another week finishing the essay using feedback (pp.1–2). Printed dates are 4pm Friday 22 October and 4pm Friday 5 November; the document gives no year. Report them as printed, not as verified current 2026 deadlines.
- Capture is hands-free; text submission does not require microphone capture. Captions stay within one rolling line, rather than growing a multi-line block.
- Assistant captions may remain until replaced; the current implementation does not require assistant captions to vanish after two seconds. Complete dialogue remains in Conversation.

### S1-09 — Toggle own captions without losing the transcript

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Open Past sessions, turn Show my captions off, close the drawer and speak a short follow-up on the same topic. Reopen the drawer and turn it on again.
2. Check Conversation after the short exchange.

**Expected:**

- The learner's voice captions obey the toggle; assistant captions remain available. The complete user transcript is still stored when own captions are hidden.
- Opening/closing the drawer does not destroy the study map. Check visible keyboard focus while operating the toggle.

### S1-10 — Interrupt a spoken answer and redirect it

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. While the tutor is speaking, say the redirect prompt. Do not wait for the old audio to finish.
2. Note whether the old request was still pending or had already committed its nodes when you interrupted.

**Copy this prompt / edit text:**

```text
Actually, explain why SEPP coursework is excluded as a project choice.
```

**Expected:**

- The brief explicitly excludes SEPP because relevant questions were already answered there (p.1). Do not continue reading out the superseded request as if the learner had not interrupted.
- Queued old audio is cut when learner speech is detected. A still-pending superseded map result must not be applied after the new request.
- Already committed nodes are not automatically deleted by an interruption. Record latency; do not assume the prototype guarantees instant device-level interruption.

### S1-11 — Pause voice; prove text-only teaching still maps explained ideas

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Pause/end voice, then switch to text. Type the learning prompt. Keep microphone capture off.
2. Wait for a text reply and inspect any new idea not already represented.

**Copy this prompt / edit text:**

```text
Help me understand the self-reflection part. What should I reflect on, according to this brief?
```

**Expected:**

- Connect the learner's own role and responsibility to a wider context of actors/stakeholders. Give help before any question, and map the explained idea if absent (p.1). Do not invent a mandatory ethical theory.
- Pausing voice closes the Live connection; switching to text must not silently restart it. Typed turns and automatic reviews still work as text.
- The submitted-text row stays visible even if a tutor error occurs. Existing concepts should be reused instead of duplicated.

### S1-12 — Expand the complete first level in one request

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Keep voice paused. Record the current labels, parents and at least one visible node position. Send the expansion prompt once.
2. Inspect the parent panel that opens after saved additions. Compare immediate groups with the reference below.

**Copy this prompt / edit text:**

```text
Expand the map structure
```

**Expected:**

- Project choice and real-world setting; essay purpose/requirements; project description, anticipated harms and personal responsibility; peer-review/revision process; advice and marking. Equivalent grouping is acceptable: these may be grouped under broader immediate children, then inspected one level deeper.
- All relevant missing immediate topics identified from the sources are added together, rather than rationed into three per request. They are blue New nodes with source-backed briefs.
- Existing labels, parents, descriptions and positions remain intact. A complete-level batch is validated atomically. The panel offers Expand subtopics and Learn this topic; it does not recursively expand every depth without a choice.

### S1-13 — Choose a subtopic silently, then expand its complete next level

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. In the branch panel choose Essay structure / Essay task (or the equivalent parent containing the essay's three components). Labels can vary; choose by meaning. Merely selecting it must be silent.
2. Click Expand subtopics once. If the source uses a broader group, choose it first and expand to reach the specified concept family. Check an existing manually placed node remains anchored.

**Expected:**

- Concise non-technical project description; potential harms and why they matter; self-reflection on role/responsibility and other stakeholders (PDF p.1). All three must be represented together at their appropriate immediate level, not released only after explain-back.
- Clicking a New child clears its New marker; simply opening a node must not start speech, a tutor turn or an edit review.
- Expansion is attached to that selected parent, not a similarly named sibling or the global root. No existing branch is renamed or reorganized.

### S1-14 — Return to the learner conversation from the branch chooser

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Click Learn this topic for the chosen branch. After the tutor helps, type 'I do not know—please explain it another way.'
2. Observe the map without first providing a correct explanation yourself.

**Expected:**

- The tutor explains the selected topic and can ask one short comprehension question afterwards. It does not require an answer before showing source-supported explained ideas as nodes.
- After 'I do not know', it gives another useful explanation/example where supported rather than repeating the same question. It preserves existing structure and does not fabricate source material.

### S1-15 — Audit durable briefs, citations, originals and explicit replay

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Open two non-root nodes in turn. Read the brief, source quotation, filename and physical PDF page/slide where applicable. Close and reopen a node and compare its brief.
2. Open the original through the node citation, and separately through the materials box. Explicitly click Hear it again. For image-backed evidence, also inspect the image-only session in step 03 if the main node cites the PDF.

**Expected:**

- Briefs are concise, source-backed and retained between openings. Citations actually support the claim; a real quote alone is not enough if its meaning is misused.
- Originals open or download appropriately. Source page numbers refer to the uploaded file, not an invented printed slide number. An explicit replay may speak; ordinary node inspection must not.
- Do not expect automatic bounding-box highlighting, original recorded microphone audio, or comprehensive diagram understanding—these are not implemented features.

### S1-16 — Exercise geometry, keyboard movement, zoom, fit, arrange and legend

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. First open a node so its New marker clears. Drag it, then focus it and use Alt+Arrow keys to move it. Record its location and content style.
2. Zoom in, zoom out, scroll the map viewport, use Fit map to screen, then explicitly use Arrange branches. Request one further branch expansion afterwards.

**Expected:**

- Moving a node changes only geometry: no red Edited marker, correction, review request or automatic speech. Keyboard movement changes position in small increments.
- Zoom/fit/scroll are usable. Explicit Arrange may change automatic layout but not meaning; saved manual positions may remain anchored. Ordinary expansion does not silently reflow existing nodes.
- Legend indicates Default, New, Edited, Corrected and Proposed removal styles; it does not mix in unrelated control instructions.

### S1-17 — Create a supported learner-authored node and watch automatic review

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Open a suitable parent; in Add a connected idea enter 'Essay length' and click Add node. Do not send a separate 'review' message.
2. While voice remains paused, observe the red Edited state and the automatic review/feedback in Conversation.

**Expected:**

- The node appears as learner-authored Edited, not as a blue system-created node. Automatic review is queued and delivered as text without restarting voice.
- A short label may be agreed with when supported; a brief pending review can be too fast to screenshot. If no review is attempted or its feedback never arrives, record a failure.

### S1-18 — Save supported content verbatim; check edit validation and Agreed

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Open Edit this node, set the label to 'Essay length' and save the exact supported description below.
2. Before the real save, try a six-word label or a blank required field; verify submission is prevented. Check the 60-character label and 600-character description limits. Restore the valid text and Save changes.

**Copy this prompt / edit text:**

```text
The required essay length is 1000 words.
```

**Expected:**

- An automatic Agreed review clears red Edited and retains the learner's exact supported wording. The citation matches the source; agreement must not silently paraphrase the saved note.
- Invalid edit fields do not corrupt the node. Reopening retains its saved brief. Source citation is not fabricated while a user-created note is still unverified.

### S1-19 — Introduce a clear misconception and inspect a correction

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Edit the same 'Essay length' node and replace its description with the incorrect statement below. Save once and wait for automatic review.
2. Record the exact original learner text, the correction, its citation and the resulting style.

**Copy this prompt / edit text:**

```text
The required essay length is 2500 words.
```

**Expected:**

- Correct to 1000 words, quoting the learner's saved 2500-word statement as the actual learner claim. Do not present a correction as a deletion proposal (p.1).
- The node becomes orange Corrected, rather than crossed out for removal. Its label/parent stay intact; the brief contains the supported correction. The learner claim is a real quote, not an invented sentence attributed to the learner.

### S1-20 — Create an unsupported topic to trigger Proposed deletion

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Under a suitable parent add a new node labelled 'Dragon feeding exam'. Leave it as this clearly unrelated topic rather than turning it into a false claim about an otherwise supported course concept.
2. Wait for automatic review without prompting it separately.

**Expected:**

- The tutor proposes deletion because this topic is unsupported by the uploaded material. The node is retained with crosslines/removal styling and a reason.
- It must not merely rename the topic or label 'no source supports this topic' as a misconception correction. If it does, record the action mismatch as a failure.

### S1-21 — Add a descendant and verify no silent cascade

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. While the unsupported parent is still present, open it and add a child labelled 'Dragon feeding schedule'. Wait for its automatic review.
2. Check both nodes remain before any confirmation.

**Expected:**

- Creating a child is supported and its review is separate. A removal proposal is not permission to delete either node.
- A proposal must not alter existing parent/child links, labels or descriptions. Record the two node names for the cascade test.

### S1-22 — Keep a proposed node

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. On 'Dragon feeding exam' choose Keep node. Reopen it and check the removal marker.
2. Do not interpret Keep as the tutor agreeing the topic is in the source.

**Expected:**

- The parent's proposal clears and the node remains. It may return to red Edited because it is still an unverified learner-authored idea; Keep does not certify it.
- A child's separate proposal need not clear when keeping the parent. The system should not immediately repeat the same proposal without new evidence.

### S1-23 — Request deletion by name; enforce action/target separation

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Type the exact request below. Watch the previously kept parent and its child; do not confirm yet.

**Copy this prompt / edit text:**

```text
Delete the Dragon feeding exam node
```

**Expected:**

- Only the named parent's removal is proposed. It stays crossed out with its child still present. No unintended rename, reparenting or orange correction substitutes for deletion.
- If speech misrecognizes a name, an ambiguous target should produce clarification rather than mutating a similarly named node.

### S1-24 — Confirm deletion and inspect descendants

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. On that proposed parent choose Confirm deletion. Do this only in the disposable test session.
2. Check the parent, its child and an unrelated supported branch.

**Expected:**

- The parent and all descendants disappear only after confirmation. Unrelated nodes, citations, geometry and conversation remain. There is no promised undo.

### S1-25 — Exercise manual Delete/Keep and root protection

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Choose another disposable supported leaf, not the corrected test node. Click Delete this node and its branches, then Keep node to cancel. Repeat and confirm deletion.
2. Open the root and inspect its controls.

**Expected:**

- Manual deletion asks for confirmation; cancel leaves the leaf intact, confirm removes it. A leaf has no unexpected cascade into another branch.
- The root can be inspected/edited but has no delete action. Deletion must not trigger an unrelated automatic correction.

### S1-26 — Inspect global history and replay

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Open Conversation from the top bar. Find the initial typed prompt, voice exchange, direct help, automatic Agreed/Corrected/removal feedback and Keep action across different topics.
2. Replay an assistant message deliberately. Close/reopen the drawer and compare the transcript.

**Expected:**

- A single session-wide history contains the whole thread; no separate node conversation is needed. Streamed fragments update one saved message rather than producing one duplicate bubble per word.
- Replay may use browser text-to-speech, not the original recorded Live voice. It must not count as a new learner turn or add a duplicate history entry. Unsent offline text is not a saved server message.

### S1-27 — Probe a source limitation without rewarding fabrication

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Ask the source-boundary prompt. Check the response against the reference pages, not against plausible general knowledge.

**Copy this prompt / edit text:**

```text
Which ethical theories and how many external references are compulsory? Point to the exact requirements in this file.
```

**Expected:**

- No named ethical theory or numerical reference quota is specified. The brief encourages defining terms, supporting arguments with course/external sources and considering counterarguments (p.2). Acknowledge what is absent rather than inventing requirements.
- The tutor states the evidence limit and offers a useful next step. It does not invent a citation, an unavailable course policy or proof that a hypothetical answer is in the file.

### S1-28 — Check a learning recap and next-step guidance

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Ask for a short recap and a useful next topic. Choose one suggested topic or use a branch panel action; do not give the tutor an artificial correct answer first.

**Copy this prompt / edit text:**

```text
Summarise what we have covered and suggest one useful next topic from my material.
```

**Expected:**

- A concise recap connects the actual thread and uploaded material. The tutor suggests a grounded next step and can expand or teach when requested; it does not restart the first-question loop.
- Newly explained ideas are mapped, existing ones reused. A complete map should not be claimed if supported topics have been omitted.

### S1-29 — Leave and reopen the main saved session

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Pause voice. Record screenshots of the map, the corrected node, a manually placed node and Conversation. Use the logo/home or New session, then reopen the main session from Past sessions in the same browser profile.
2. Verify original files and the recorded brief after reopening. Do not sign in again or clear cookies mid-test.

**Expected:**

- The map, saved labels/descriptions, review states, manual positions, source files and complete history are retained. Opening the session does not inject scripted demo material.
- New/acknowledged state is retained appropriately. The camera/zoom and which panel is open need not persist; those are UI state, not saved learning content.

### S1-30 — Test backend disconnect and readable unsent-text feedback

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. With the main run saved and voice paused, perform Procedure A below on the local service. While disconnected, submit a short message and copy it from the You row before reloading.
2. Restart using the same local environment/database, reload in the same profile and reopen the session. Re-enter the unsent message only after reconnection.

**Expected:**

- Connection loss and an unsent message produce clear feedback, not a raw HTTP traceback/status banner. The app does not falsely claim an offline request reached the tutor.
- Previously saved map/history/originals survive a normal local restart. An unsent message and the dock's transient row are not promised to survive a page reload. No database reset is needed.

### S1-31 — Test voice-only failure and rollback without disabling the tutor

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Perform Procedure B below: use an invalid Live model temporarily while keeping the API key, tutor model and database unchanged. Reopen the saved session and send a typed learning question; save a supported edit too.
2. Restore the original Live model. Then perform Procedure C to smoke-test chained mode with one typed and one spoken question, restore live mode, restart and reopen.

**Expected:**

- Live startup failure leaves independent text and automatic edit review usable, with clear errors. A user edit remains saved even if review fails; no fake agreement is displayed.
- Chained mode remains a working rollback path if its configured speech models are available. Restoring live reconnects with saved study context. Record provider-access failures as Blocked with evidence, not Pass.

### S1-32 — Check browser ownership isolation

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Use a different browser profile or browser application. Sign in with the same shared credentials and open Past sessions. Do not merely open another tab or another private window sharing the same private cookie jar.
2. Close the second profile and return to the original profile.

**Expected:**

- The second login does not inherit the first browser's session library: these credentials do not implement cross-browser accounts. No original file or conversation from the first owner is exposed.
- The original profile still accesses its own test session. Do not clear its cookie while testing persistence.

### S1-33 — Cancel and confirm session deletion; finish the report

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Export the test results and save screenshots before deletion. In Past sessions click Delete on the main test session, cancel once, then repeat and confirm.
2. Clean up only this scenario's disposable sessions. Keep the fixture pack and original learning PDFs. Mark every step Pass, Fail or Blocked and explain any deviation.

**Expected:**

- Cancel preserves the session. Confirm removes its map, stored dialogue and stored upload copies; it no longer reopens from Past sessions. The original PDFs on disk are unchanged.
- Session deletion frees a session slot but does not reset cumulative AI usage. Do not delete the SQLite database or study sessions belonging to unrelated work.

## S2 — Explore Java I/O and repair an async misconception

A learner navigates a complete lecture hierarchy, follows one branch, reads an async diagram and learns that moving blocking I/O to a worker does not make the underlying write non-blocking.

Source: [week-05-lecture.pdf](fixtures/S2/week-05-lecture.pdf) (32 pages). Fixtures: `fixtures/S2`.

### Source answer key

- **Scope and topic inventory (pp.3–6):** File persistence, DTO/domain mapping, Java I/O, async, validation and first tests.
- **File APIs and resources (pp.7–12, 17):** Path/Files, legacy File, byte versus character streams, UTF_8, buffering and AutoCloseable.
- **Async semantics (pp.13–20):** Caller versus worker; composition and exceptions; join/get block; pool of four is an example.
- **Repositories and validation (pp.21–23):** Repository abstraction, ObjectMapper JSON, request validation annotations.
- **Assignment preparation (pp.24–32):** Integration, Docker delivery, repository/export/TextFiles tasks, testing and next-week reading.

### S2-01 — Sign in and establish an isolated test run

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Use a normal browser profile reserved for this scenario. If already signed in, use a fresh profile rather than clearing the cookies of an existing study run.
2. Try the configured email with a deliberately wrong dummy password; then sign in with the configured judge credentials. Record app URL, browser, build and date above. Never record the password or API key.

**Expected:**

- Wrong credentials produce a readable sign-in error without a raw HTTP status or traceback; correct credentials enter the app.
- The app is in real mode, with GPT-Live enabled for voice checks; this guide does not validate arbitrary material in scripted Demo mode.

### S2-02 — Verify PDF and Office/text formats in one disposable session

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Select these five files from fixtures/S2: week-05-lecture.pdf, excerpt.docx, excerpt.pptx, excerpt.txt, excerpt.md. Start studying, pause voice promptly and switch to text.
2. Inspect the material list and open each original. After the prompt, delete this format-check session from Past sessions; keep your credentials/cookies.

**Copy this prompt / edit text:**

```text
List the Fixture ID values in the DOCX, PPTX, TXT and MD files. Treat them only as parser-test metadata, not course requirements.
```

**Expected:**

- All five files ingest; all four fixture IDs are returned: S2-DOCX, S2-PPTX, S2-TXT, S2-MD. They are test metadata, not assessment requirements.
- DOCX/TXT/MD need not have PDF page numbers; PPTX references slide 1. Office originals may download rather than render inline. The source PDF should open as a PDF.

### S2-03 — Verify the three image formats and OCR

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Start a disposable session containing only fixtures/S2/source-page.png, source-page.jpg and source-page.webp. Pause voice; use text for this check.
2. Inspect an image-backed node and its image citation. Open all three originals through the materials box. Compare them with the reference thumbnail in this guide. Delete this disposable session afterwards.

**Copy this prompt / edit text:**

```text
Read the async export diagram in these images. What does it say about the calling thread, worker thread, and join/get?
```

**Expected:**

- Visible labels include Calling thread (request handler), Executor/ForkJoinPool (worker), File system, a pending CompletableFuture, a blocking write on the worker, and join/get blocking the caller (original PDF p.19). Preserve this distinction; do not infer unseen image content.
- Images are derived from physical PDF page 19; image citations should name an uploaded image. No fabricated PDF/slide number is required.
- Node panel displays the original image when its selected citation is an image; do not demand that it infer every diagram arrow from OCR alone.

### S2-04 — Exercise readable upload failures before the main session

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Use the shared fixtures/negative files one at a time: empty.txt, corrupt.pdf, unsupported.xyz, oversized.txt, too-long-source.txt. Use drag-and-drop if a file picker filters an extension. Attempt Start studying after each; remove the failed selection before the next check.
2. Select six valid files at once: original PDF plus excerpt.docx, excerpt.pptx, excerpt.txt, excerpt.md and source-page.png. Attempt Start, then remove extras.

**Expected:**

- Zero-byte, unreadable PDF, unsupported type, >10 MB and >40,000 extracted characters each produce an actionable message without a raw '400 Bad Request' banner or traceback.
- Six files are rejected with a one-to-five-file message. No half-created study session appears. After removing bad files, normal upload works. These tests do not require exhausting paid quotas.

### S2-05 — Manage selections for the main learning session

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. From fixtures/S2, use both drag-and-drop and the empty study box to select week-05-lecture.pdf, source-page.png and excerpt.txt.
2. Add excerpt.md temporarily. Click the populated box, verify filenames/count, Remove excerpt.md, then use Add files and remove it again. Close/reopen the list and confirm the final set.

**Expected:**

- The clickable box opens selection management. Removed files disappear from the submitted list. No redundant standalone Browse control is needed.
- Start becomes usable after the file-card animation settles. Main session has three files (four in S3), within the five-file limit. Original PDFs are unchanged on disk.

### S2-06 — Start with a root; demonstrate microphone denial without losing text

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Start studying. Initially deny microphone permission if prompted. If permission was already granted, block it in this test profile's site controls and reopen the session; do not clear cookies.
2. Switch to keyboard mode. Pause/end voice so long checklist work does not keep a paid voice connection running. Record the main session title and ID/URL if available.

**Expected:**

- The initial map has one root, and session creation finishes. A voice welcome is allowed when audio is available; it is not proof of source mastery.
- A microphone problem is readable, and text remains usable. No login bypass, scripted backpropagation material or raw provider error should appear.

### S2-07 — Submit a direct help request and verify immediate visible feedback

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Type the prompt and press Enter. Watch the input dock immediately, then while waiting and while the response appears. Expand the You row to read the full submitted text.
2. Do not repeat the concept first just to make the map populate.

**Copy this prompt / edit text:**

```text
Explain how synchronous and asynchronous file export differ in this lecture. Show the ideas you explain as map nodes immediately.
```

**Expected:**

- Your latest typed message remains visible in the expandable You row after the input clears. Thinking… is visible while the backend is pending and not speaking an acknowledgement.
- Synchronous I/O blocks the calling thread (p.13). The illustrated async export returns a CompletableFuture while a worker does the write (pp.14–19).
- The write itself still blocks the worker thread; join()/get() can block the caller (pp.15, 19–20). Do not claim async always runs faster or never blocks any thread.
- Create source-backed New nodes for newly explained ideas without demanding learner repetition.
- Newly explained, supported ideas become blue New nodes now; the tutor must not keep asking what you know instead of helping.

### S2-08 — Allow voice and check hands-free input and rolling captions

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Allow microphone access again in site controls. Return to voice mode, use the explicit pause/resume control if necessary, and speak the prompt normally, followed by a short pause.
2. Watch the active speaker and one-line rolling captions. Compare the saved user transcript with what you said.

**Copy this prompt / edit text:**

```text
Explain the async export diagram: who returns immediately and which thread waits for the file write?
```

**Expected:**

- The calling/request thread receives a pending future and can continue; an executor/ForkJoinPool worker performs the blocking write; completion resolves the future and a callback handles the result (p.19).
- Capture is hands-free; text submission does not require microphone capture. Captions stay within one rolling line, rather than growing a multi-line block.
- Assistant captions may remain until replaced; the current implementation does not require assistant captions to vanish after two seconds. Complete dialogue remains in Conversation.

### S2-09 — Toggle own captions without losing the transcript

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Open Past sessions, turn Show my captions off, close the drawer and speak a short follow-up on the same topic. Reopen the drawer and turn it on again.
2. Check Conversation after the short exchange.

**Expected:**

- The learner's voice captions obey the toggle; assistant captions remain available. The complete user transcript is still stored when own captions are hidden.
- Opening/closing the drawer does not destroy the study map. Check visible keyboard focus while operating the toggle.

### S2-10 — Interrupt a spoken answer and redirect it

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. While the tutor is speaking, say the redirect prompt. Do not wait for the old audio to finish.
2. Note whether the old request was still pending or had already committed its nodes when you interrupted.

**Copy this prompt / edit text:**

```text
Actually, explain what happens if I immediately call join on that future.
```

**Expected:**

- join() blocks the caller until the future completes; it can defeat the caller-responsiveness benefit. Do not say every asynchronous API makes the underlying disk write non-blocking (pp.15, 19–20).
- Queued old audio is cut when learner speech is detected. A still-pending superseded map result must not be applied after the new request.
- Already committed nodes are not automatically deleted by an interruption. Record latency; do not assume the prototype guarantees instant device-level interruption.

### S2-11 — Pause voice; prove text-only teaching still maps explained ideas

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Pause/end voice, then switch to text. Type the learning prompt. Keep microphone capture off.
2. Wait for a text reply and inspect any new idea not already represented.

**Copy this prompt / edit text:**

```text
Explain thenApply versus thenAccept using this lecture. Add any newly explained concepts to the map.
```

**Expected:**

- thenApply transforms the value; thenAccept consumes it. Reuse nodes already present and add missing concepts, without an explain-back gate (pp.15, 20).
- Pausing voice closes the Live connection; switching to text must not silently restart it. Typed turns and automatic reviews still work as text.
- The submitted-text row stays visible even if a tutor error occurs. Existing concepts should be reused instead of duplicated.

### S2-12 — Expand the complete first level in one request

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Keep voice paused. Record the current labels, parents and at least one visible node position. Send the expansion prompt once.
2. Inspect the parent panel that opens after saved additions. Compare immediate groups with the reference below.

**Copy this prompt / edit text:**

```text
Expand the map structure
```

**Expected:**

- DTO/domain transformation and Jackson; file/JSON persistence and repositories; Java Path/Paths/File/Files; byte/character streams, buffering/charsets/resources; sync/async and futures/executors/errors; validation/global errors; service/mapper tests; assignment/Docker delivery and preparation/reading (pp.3–6, 24–32). Sensible parent groups are acceptable; a three-topic sample is not a complete overview.
- All relevant missing immediate topics identified from the sources are added together, rather than rationed into three per request. They are blue New nodes with source-backed briefs.
- Existing labels, parents, descriptions and positions remain intact. A complete-level batch is validated atomically. The panel offers Expand subtopics and Learn this topic; it does not recursively expand every depth without a choice.

### S2-13 — Choose a subtopic silently, then expand its complete next level

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. In the branch panel choose Asynchronous I/O / CompletableFuture (the parent containing async composition). Labels can vary; choose by meaning. Merely selecting it must be silent.
2. Click Expand subtopics once. If the source uses a broader group, choose it first and expand to reach the specified concept family. Check an existing manually placed node remains anchored.

**Expected:**

- Creation/worker execution (runAsync/supplyAsync); transformation (thenApply); consumption (thenAccept); chaining (thenCompose); recovery (exceptionally); combining futures (allOf); blocking waits (join/get); executors and checked-exception wrapping (pp.14–20). Equivalent grouping is acceptable, but all relevant immediate groups must appear together; choose a group to inspect its next level.
- Clicking a New child clears its New marker; simply opening a node must not start speech, a tutor turn or an edit review.
- Expansion is attached to that selected parent, not a similarly named sibling or the global root. No existing branch is renamed or reorganized.

### S2-14 — Return to the learner conversation from the branch chooser

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Click Learn this topic for the chosen branch. After the tutor helps, type 'I do not know—please explain it another way.'
2. Observe the map without first providing a correct explanation yourself.

**Expected:**

- The tutor explains the selected topic and can ask one short comprehension question afterwards. It does not require an answer before showing source-supported explained ideas as nodes.
- After 'I do not know', it gives another useful explanation/example where supported rather than repeating the same question. It preserves existing structure and does not fabricate source material.

### S2-15 — Audit durable briefs, citations, originals and explicit replay

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Open two non-root nodes in turn. Read the brief, source quotation, filename and physical PDF page/slide where applicable. Close and reopen a node and compare its brief.
2. Open the original through the node citation, and separately through the materials box. Explicitly click Hear it again. For image-backed evidence, also inspect the image-only session in step 03 if the main node cites the PDF.

**Expected:**

- Briefs are concise, source-backed and retained between openings. Citations actually support the claim; a real quote alone is not enough if its meaning is misused.
- Originals open or download appropriately. Source page numbers refer to the uploaded file, not an invented printed slide number. An explicit replay may speak; ordinary node inspection must not.
- Do not expect automatic bounding-box highlighting, original recorded microphone audio, or comprehensive diagram understanding—these are not implemented features.

### S2-16 — Exercise geometry, keyboard movement, zoom, fit, arrange and legend

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. First open a node so its New marker clears. Drag it, then focus it and use Alt+Arrow keys to move it. Record its location and content style.
2. Zoom in, zoom out, scroll the map viewport, use Fit map to screen, then explicitly use Arrange branches. Request one further branch expansion afterwards.

**Expected:**

- Moving a node changes only geometry: no red Edited marker, correction, review request or automatic speech. Keyboard movement changes position in small increments.
- Zoom/fit/scroll are usable. Explicit Arrange may change automatic layout but not meaning; saved manual positions may remain anchored. Ordinary expansion does not silently reflow existing nodes.
- Legend indicates Default, New, Edited, Corrected and Proposed removal styles; it does not mix in unrelated control instructions.

### S2-17 — Create a supported learner-authored node and watch automatic review

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Open a suitable parent; in Add a connected idea enter 'Joining futures' and click Add node. Do not send a separate 'review' message.
2. While voice remains paused, observe the red Edited state and the automatic review/feedback in Conversation.

**Expected:**

- The node appears as learner-authored Edited, not as a blue system-created node. Automatic review is queued and delivered as text without restarting voice.
- A short label may be agreed with when supported; a brief pending review can be too fast to screenshot. If no review is attempted or its feedback never arrives, record a failure.

### S2-18 — Save supported content verbatim; check edit validation and Agreed

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Open Edit this node, set the label to 'Joining futures' and save the exact supported description below.
2. Before the real save, try a six-word label or a blank required field; verify submission is prevented. Check the 60-character label and 600-character description limits. Restore the valid text and Save changes.

**Copy this prompt / edit text:**

```text
join() and get() block the caller until the result is ready.
```

**Expected:**

- An automatic Agreed review clears red Edited and retains the learner's exact supported wording. The citation matches the source; agreement must not silently paraphrase the saved note.
- Invalid edit fields do not corrupt the node. Reopening retains its saved brief. Source citation is not fabricated while a user-created note is still unverified.

### S2-19 — Introduce a clear misconception and inspect a correction

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Edit the same 'Joining futures' node and replace its description with the incorrect statement below. Save once and wait for automatic review.
2. Record the exact original learner text, the correction, its citation and the resulting style.

**Copy this prompt / edit text:**

```text
Calling join() never blocks the calling thread.
```

**Expected:**

- Correct to a blocking wait, citing pp.15, 19 or 20 and quoting the actual saved incorrect sentence. Keep the node and hierarchy; do not rename it or propose deletion merely because the claim is wrong.
- The node becomes orange Corrected, rather than crossed out for removal. Its label/parent stay intact; the brief contains the supported correction. The learner claim is a real quote, not an invented sentence attributed to the learner.

### S2-20 — Create an unsupported topic to trigger Proposed deletion

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Under a suitable parent add a new node labelled 'Dragon breeding'. Leave it as this clearly unrelated topic rather than turning it into a false claim about an otherwise supported course concept.
2. Wait for automatic review without prompting it separately.

**Expected:**

- The tutor proposes deletion because this topic is unsupported by the uploaded material. The node is retained with crosslines/removal styling and a reason.
- It must not merely rename the topic or label 'no source supports this topic' as a misconception correction. If it does, record the action mismatch as a failure.

### S2-21 — Add a descendant and verify no silent cascade

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. While the unsupported parent is still present, open it and add a child labelled 'Dragon feeding plan'. Wait for its automatic review.
2. Check both nodes remain before any confirmation.

**Expected:**

- Creating a child is supported and its review is separate. A removal proposal is not permission to delete either node.
- A proposal must not alter existing parent/child links, labels or descriptions. Record the two node names for the cascade test.

### S2-22 — Keep a proposed node

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. On 'Dragon breeding' choose Keep node. Reopen it and check the removal marker.
2. Do not interpret Keep as the tutor agreeing the topic is in the source.

**Expected:**

- The parent's proposal clears and the node remains. It may return to red Edited because it is still an unverified learner-authored idea; Keep does not certify it.
- A child's separate proposal need not clear when keeping the parent. The system should not immediately repeat the same proposal without new evidence.

### S2-23 — Request deletion by name; enforce action/target separation

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Type the exact request below. Watch the previously kept parent and its child; do not confirm yet.

**Copy this prompt / edit text:**

```text
Delete the Dragon breeding node
```

**Expected:**

- Only the named parent's removal is proposed. It stays crossed out with its child still present. No unintended rename, reparenting or orange correction substitutes for deletion.
- If speech misrecognizes a name, an ambiguous target should produce clarification rather than mutating a similarly named node.

### S2-24 — Confirm deletion and inspect descendants

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. On that proposed parent choose Confirm deletion. Do this only in the disposable test session.
2. Check the parent, its child and an unrelated supported branch.

**Expected:**

- The parent and all descendants disappear only after confirmation. Unrelated nodes, citations, geometry and conversation remain. There is no promised undo.

### S2-25 — Exercise manual Delete/Keep and root protection

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Choose another disposable supported leaf, not the corrected test node. Click Delete this node and its branches, then Keep node to cancel. Repeat and confirm deletion.
2. Open the root and inspect its controls.

**Expected:**

- Manual deletion asks for confirmation; cancel leaves the leaf intact, confirm removes it. A leaf has no unexpected cascade into another branch.
- The root can be inspected/edited but has no delete action. Deletion must not trigger an unrelated automatic correction.

### S2-26 — Inspect global history and replay

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Open Conversation from the top bar. Find the initial typed prompt, voice exchange, direct help, automatic Agreed/Corrected/removal feedback and Keep action across different topics.
2. Replay an assistant message deliberately. Close/reopen the drawer and compare the transcript.

**Expected:**

- A single session-wide history contains the whole thread; no separate node conversation is needed. Streamed fragments update one saved message rather than producing one duplicate bubble per word.
- Replay may use browser text-to-speech, not the original recorded Live voice. It must not count as a new learner turn or add a duplicate history entry. Unsent offline text is not a saved server message.

### S2-27 — Probe a source limitation without rewarding fabrication

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Ask the source-boundary prompt. Check the response against the reference pages, not against plausible general knowledge.

**Copy this prompt / edit text:**

```text
Does this deck prove that asynchronous export always finishes faster, or specify the optimal thread-pool size for my machine?
```

**Expected:**

- No. It demonstrates caller responsiveness and explicit executor/error handling, not a universal throughput guarantee or benchmark-derived optimal pool size (pp.14–20). The example pool of four on p.16 is an example, not an experimentally established optimum.
- The tutor states the evidence limit and offers a useful next step. It does not invent a citation, an unavailable course policy or proof that a hypothetical answer is in the file.

### S2-28 — Check a learning recap and next-step guidance

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Ask for a short recap and a useful next topic. Choose one suggested topic or use a branch panel action; do not give the tutor an artificial correct answer first.

**Copy this prompt / edit text:**

```text
Summarise what we have covered and suggest one useful next topic from my material.
```

**Expected:**

- A concise recap connects the actual thread and uploaded material. The tutor suggests a grounded next step and can expand or teach when requested; it does not restart the first-question loop.
- Newly explained ideas are mapped, existing ones reused. A complete map should not be claimed if supported topics have been omitted.

### S2-29 — Leave and reopen the main saved session

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Pause voice. Record screenshots of the map, the corrected node, a manually placed node and Conversation. Use the logo/home or New session, then reopen the main session from Past sessions in the same browser profile.
2. Verify original files and the recorded brief after reopening. Do not sign in again or clear cookies mid-test.

**Expected:**

- The map, saved labels/descriptions, review states, manual positions, source files and complete history are retained. Opening the session does not inject scripted demo material.
- New/acknowledged state is retained appropriately. The camera/zoom and which panel is open need not persist; those are UI state, not saved learning content.

### S2-30 — Test backend disconnect and readable unsent-text feedback

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. With the main run saved and voice paused, perform Procedure A below on the local service. While disconnected, submit a short message and copy it from the You row before reloading.
2. Restart using the same local environment/database, reload in the same profile and reopen the session. Re-enter the unsent message only after reconnection.

**Expected:**

- Connection loss and an unsent message produce clear feedback, not a raw HTTP traceback/status banner. The app does not falsely claim an offline request reached the tutor.
- Previously saved map/history/originals survive a normal local restart. An unsent message and the dock's transient row are not promised to survive a page reload. No database reset is needed.

### S2-31 — Test voice-only failure and rollback without disabling the tutor

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Perform Procedure B below: use an invalid Live model temporarily while keeping the API key, tutor model and database unchanged. Reopen the saved session and send a typed learning question; save a supported edit too.
2. Restore the original Live model. Then perform Procedure C to smoke-test chained mode with one typed and one spoken question, restore live mode, restart and reopen.

**Expected:**

- Live startup failure leaves independent text and automatic edit review usable, with clear errors. A user edit remains saved even if review fails; no fake agreement is displayed.
- Chained mode remains a working rollback path if its configured speech models are available. Restoring live reconnects with saved study context. Record provider-access failures as Blocked with evidence, not Pass.

### S2-32 — Check browser ownership isolation

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Use a different browser profile or browser application. Sign in with the same shared credentials and open Past sessions. Do not merely open another tab or another private window sharing the same private cookie jar.
2. Close the second profile and return to the original profile.

**Expected:**

- The second login does not inherit the first browser's session library: these credentials do not implement cross-browser accounts. No original file or conversation from the first owner is exposed.
- The original profile still accesses its own test session. Do not clear its cookie while testing persistence.

### S2-33 — Cancel and confirm session deletion; finish the report

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Export the test results and save screenshots before deletion. In Past sessions click Delete on the main test session, cancel once, then repeat and confirm.
2. Clean up only this scenario's disposable sessions. Keep the fixture pack and original learning PDFs. Mark every step Pass, Fail or Blocked and explain any deviation.

**Expected:**

- Cancel preserves the session. Confirm removes its map, stored dialogue and stored upload copies; it no longer reopens from Past sessions. The original PDFs on disk are unchanged.
- Session deletion frees a session slot but does not reset cumulative AI usage. Do not delete the SQLite database or study sessions belonging to unrelated work.

## S3 — Diagnose a REST lab and connect it to file persistence

A learner explains the CampusShop request/error flow, corrects duplicate-order handling, navigates all lab tasks and distinguishes Week 4 in-memory storage from Week 5 file persistence.

Source: [week-04-lab-student.pdf](fixtures/S3/week-04-lab-student.pdf) (4 pages). Fixtures: `fixtures/S3`.

### Source answer key

- **Architecture and storage (lab p.1):** Controller → service → in-memory repository; @Valid happens before the controller body; Week 5 adds file persistence.
- **Project responsibilities (lab p.2):** Student implements service methods, global handlers and Dockerfile; four controller tests are the definition of done.
- **Core error mappings (lab p.3):** 400 validation; 400 malformed JSON; 404 missing; 409 duplicate. Catch-all 500 is a stretch goal.
- **Config, health and delivery (lab pp.1–4):** Uniqueness flag, SERVER_PORT example, Actuator, Docker build/run/save/load and reflection questions.
- **Cross-document distinction (lecture pp.21–22, 30–31):** Week 5 adds file/JSON repositories and sync/async export; do not retroactively change Week 4's storage.

### S3-01 — Sign in and establish an isolated test run

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Use a normal browser profile reserved for this scenario. If already signed in, use a fresh profile rather than clearing the cookies of an existing study run.
2. Try the configured email with a deliberately wrong dummy password; then sign in with the configured judge credentials. Record app URL, browser, build and date above. Never record the password or API key.

**Expected:**

- Wrong credentials produce a readable sign-in error without a raw HTTP status or traceback; correct credentials enter the app.
- The app is in real mode, with GPT-Live enabled for voice checks; this guide does not validate arbitrary material in scripted Demo mode.

### S3-02 — Verify PDF and Office/text formats in one disposable session

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Select these five files from fixtures/S3: week-04-lab-student.pdf, excerpt.docx, excerpt.pptx, excerpt.txt, excerpt.md. Start studying, pause voice promptly and switch to text.
2. Inspect the material list and open each original. After the prompt, delete this format-check session from Past sessions; keep your credentials/cookies.

**Copy this prompt / edit text:**

```text
List the Fixture ID values in the DOCX, PPTX, TXT and MD files. Treat them only as parser-test metadata, not course requirements.
```

**Expected:**

- All five files ingest; all four fixture IDs are returned: S3-DOCX, S3-PPTX, S3-TXT, S3-MD. They are test metadata, not assessment requirements.
- DOCX/TXT/MD need not have PDF page numbers; PPTX references slide 1. Office originals may download rather than render inline. The source PDF should open as a PDF.

### S3-03 — Verify the three image formats and OCR

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Start a disposable session containing only fixtures/S3/source-page.png, source-page.jpg and source-page.webp. Pause voice; use text for this check.
2. Inspect an image-backed node and its image citation. Open all three originals through the materials box. Compare them with the reference thumbnail in this guide. Delete this disposable session afterwards.

**Copy this prompt / edit text:**

```text
Read the exception mappings in these images. Which status belongs to duplicate orders, and which handler is only a stretch goal?
```

**Expected:**

- 409 DUPLICATE_ORDER is core; a catch-all Exception.class → 500 INTERNAL_ERROR handler is a stretch goal (original lab p.3). Cite the supplied image filename in an image-only session.
- Images are derived from physical PDF page 3; image citations should name an uploaded image. No fabricated PDF/slide number is required.
- Node panel displays the original image when its selected citation is an image; do not demand that it infer every diagram arrow from OCR alone.

### S3-04 — Exercise readable upload failures before the main session

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Use the shared fixtures/negative files one at a time: empty.txt, corrupt.pdf, unsupported.xyz, oversized.txt, too-long-source.txt. Use drag-and-drop if a file picker filters an extension. Attempt Start studying after each; remove the failed selection before the next check.
2. Select six valid files at once: original PDF plus excerpt.docx, excerpt.pptx, excerpt.txt, excerpt.md and source-page.png. Attempt Start, then remove extras.

**Expected:**

- Zero-byte, unreadable PDF, unsupported type, >10 MB and >40,000 extracted characters each produce an actionable message without a raw '400 Bad Request' banner or traceback.
- Six files are rejected with a one-to-five-file message. No half-created study session appears. After removing bad files, normal upload works. These tests do not require exhausting paid quotas.

### S3-05 — Manage selections for the main learning session

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. From fixtures/S3, use both drag-and-drop and the empty study box to select week-04-lab-student.pdf, source-page.png and excerpt.txt, plus week-05-lecture.pdf (included in this folder for cross-document checks).
2. Add excerpt.md temporarily. Click the populated box, verify filenames/count, Remove excerpt.md, then use Add files and remove it again. Close/reopen the list and confirm the final set.

**Expected:**

- The clickable box opens selection management. Removed files disappear from the submitted list. No redundant standalone Browse control is needed.
- Start becomes usable after the file-card animation settles. Main session has three files (four in S3), within the five-file limit. Original PDFs are unchanged on disk.

### S3-06 — Start with a root; demonstrate microphone denial without losing text

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Start studying. Initially deny microphone permission if prompted. If permission was already granted, block it in this test profile's site controls and reopen the session; do not clear cookies.
2. Switch to keyboard mode. Pause/end voice so long checklist work does not keep a paid voice connection running. Record the main session title and ID/URL if available.

**Expected:**

- The initial map has one root, and session creation finishes. A voice welcome is allowed when audio is available; it is not proof of source mastery.
- A microphone problem is readable, and text remains usable. No login bypass, scripted backpropagation material or raw provider error should appear.

### S3-07 — Submit a direct help request and verify immediate visible feedback

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Type the prompt and press Enter. Watch the input dock immediately, then while waiting and while the response appears. Expand the You row to read the full submitted text.
2. Do not repeat the concept first just to make the map populate.

**Copy this prompt / edit text:**

```text
Explain what happens when POST /partner-orders receives a valid order and when an order is duplicated. Map the ideas you explain without waiting for me to repeat them.
```

**Expected:**

- Your latest typed message remains visible in the expandable You row after the input clears. Thinking… is visible while the backend is pending and not speaking an acknowledgement.
- Controller → service → repository; service generates a UUID, maps, saves and logs with context (lab pp.1–3).
- When uniqueness is enabled, a duplicate triggers DuplicateOrderException, mapped centrally to 409 DUPLICATE_ORDER (lab p.3).
- Week 4 storage is InMemoryOrderRepository; file persistence is introduced in Week 5. Do not silently mix the two versions.
- Newly explained, supported ideas become blue New nodes now; the tutor must not keep asking what you know instead of helping.

### S3-08 — Allow voice and check hands-free input and rolling captions

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Allow microphone access again in site controls. Return to voice mode, use the explicit pause/resume control if necessary, and speak the prompt normally, followed by a short pause.
2. Watch the active speaker and one-line rolling captions. Compare the saved user transcript with what you said.

**Copy this prompt / edit text:**

```text
Why does invalid input not reach OrderService, and which error response should it produce?
```

**Expected:**

- @Valid runs before the controller method body; invalid input becomes MethodArgumentNotValidException and is handled centrally as 400 VALIDATION_FAILED with field errors (lab pp.1, 3).
- Capture is hands-free; text submission does not require microphone capture. Captions stay within one rolling line, rather than growing a multi-line block.
- Assistant captions may remain until replaced; the current implementation does not require assistant captions to vanish after two seconds. Complete dialogue remains in Conversation.

### S3-09 — Toggle own captions without losing the transcript

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Open Past sessions, turn Show my captions off, close the drawer and speak a short follow-up on the same topic. Reopen the drawer and turn it on again.
2. Check Conversation after the short exchange.

**Expected:**

- The learner's voice captions obey the toggle; assistant captions remain available. The complete user transcript is still stored when own captions are hidden.
- Opening/closing the drawer does not destroy the study map. Check visible keyboard focus while operating the toggle.

### S3-10 — Interrupt a spoken answer and redirect it

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. While the tutor is speaking, say the redirect prompt. Do not wait for the old audio to finish.
2. Note whether the old request was still pending or had already committed its nodes when you interrupted.

**Copy this prompt / edit text:**

```text
Actually, explain the difference between Week 4 storage and Week 5 persistence.
```

**Expected:**

- Week 4 explicitly stays in-memory (lab p.1). Week 5 introduces file-based JSON repositories and export (lecture pp.21–22, 30–31). Explain the chronology; do not call these documents contradictory or invent code that was not uploaded.
- Queued old audio is cut when learner speech is detected. A still-pending superseded map result must not be applied after the new request.
- Already committed nodes are not automatically deleted by an interruption. Record latency; do not assume the prototype guarantees instant device-level interruption.

### S3-11 — Pause voice; prove text-only teaching still maps explained ideas

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Pause/end voice, then switch to text. Type the learning prompt. Keep microphone capture off.
2. Wait for a text reply and inspect any new idea not already represented.

**Copy this prompt / edit text:**

```text
Why is a duplicate order not a 500 error here, and where should the mapping happen?
```

**Expected:**

- It is an expected domain conflict, mapped to 409 DUPLICATE_ORDER by GlobalExceptionHandler/@ExceptionHandler, not an unexpected server failure. Map new explained concepts immediately (lab pp.1–3).
- Pausing voice closes the Live connection; switching to text must not silently restart it. Typed turns and automatic reviews still work as text.
- The submitted-text row stays visible even if a tutor error occurs. Existing concepts should be reused instead of duplicated.

### S3-12 — Expand the complete first level in one request

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Keep voice paused. Record the current labels, parents and at least one visible node position. Send the expansion prompt once.
2. Inspect the parent panel that opens after saved additions. Compare immediate groups with the reference below.

**Copy this prompt / edit text:**

```text
Expand the map structure
```

**Expected:**

- Week 4 request/layer flow, service import/find logic, validation and four core exception mappings, contextual logging, configuration/precedence, Actuator health, Docker build/run/save/load, four tests and stretch/reflection items (lab pp.1–4). With Week 5 also uploaded, separate its file-persistence/export material from Week 4 storage.
- All relevant missing immediate topics identified from the sources are added together, rather than rationed into three per request. They are blue New nodes with source-backed briefs.
- Existing labels, parents, descriptions and positions remain intact. A complete-level batch is validated atomically. The panel offers Expand subtopics and Learn this topic; it does not recursively expand every depth without a choice.

### S3-13 — Choose a subtopic silently, then expand its complete next level

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. In the branch panel choose Global exception handling / Error mapping in the Week 4 lab. Labels can vary; choose by meaning. Merely selecting it must be silent.
2. Click Expand subtopics once. If the source uses a broader group, choose it first and expand to reach the specified concept family. Check an existing manually placed node remains anchored.

**Expected:**

- Validation → 400 VALIDATION_FAILED with field errors; malformed request → 400 MALFORMED_REQUEST; missing order → 404 ORDER_NOT_FOUND; duplicate → 409 DUPLICATE_ORDER (lab p.3). The catch-all 500 INTERNAL_ERROR is a stretch goal, not one of the four core TODO handlers. All four core mappings must be available together, with optional material clearly labelled.
- Clicking a New child clears its New marker; simply opening a node must not start speech, a tutor turn or an edit review.
- Expansion is attached to that selected parent, not a similarly named sibling or the global root. No existing branch is renamed or reorganized.

### S3-14 — Return to the learner conversation from the branch chooser

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Click Learn this topic for the chosen branch. After the tutor helps, type 'I do not know—please explain it another way.'
2. Observe the map without first providing a correct explanation yourself.

**Expected:**

- The tutor explains the selected topic and can ask one short comprehension question afterwards. It does not require an answer before showing source-supported explained ideas as nodes.
- After 'I do not know', it gives another useful explanation/example where supported rather than repeating the same question. It preserves existing structure and does not fabricate source material.

### S3-15 — Audit durable briefs, citations, originals and explicit replay

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Open two non-root nodes in turn. Read the brief, source quotation, filename and physical PDF page/slide where applicable. Close and reopen a node and compare its brief.
2. Open the original through the node citation, and separately through the materials box. Explicitly click Hear it again. For image-backed evidence, also inspect the image-only session in step 03 if the main node cites the PDF.

**Expected:**

- Briefs are concise, source-backed and retained between openings. Citations actually support the claim; a real quote alone is not enough if its meaning is misused.
- Originals open or download appropriately. Source page numbers refer to the uploaded file, not an invented printed slide number. An explicit replay may speak; ordinary node inspection must not.
- Do not expect automatic bounding-box highlighting, original recorded microphone audio, or comprehensive diagram understanding—these are not implemented features.

### S3-16 — Exercise geometry, keyboard movement, zoom, fit, arrange and legend

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. First open a node so its New marker clears. Drag it, then focus it and use Alt+Arrow keys to move it. Record its location and content style.
2. Zoom in, zoom out, scroll the map viewport, use Fit map to screen, then explicitly use Arrange branches. Request one further branch expansion afterwards.

**Expected:**

- Moving a node changes only geometry: no red Edited marker, correction, review request or automatic speech. Keyboard movement changes position in small increments.
- Zoom/fit/scroll are usable. Explicit Arrange may change automatic layout but not meaning; saved manual positions may remain anchored. Ordinary expansion does not silently reflow existing nodes.
- Legend indicates Default, New, Edited, Corrected and Proposed removal styles; it does not mix in unrelated control instructions.

### S3-17 — Create a supported learner-authored node and watch automatic review

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Open a suitable parent; in Add a connected idea enter 'Duplicate orders' and click Add node. Do not send a separate 'review' message.
2. While voice remains paused, observe the red Edited state and the automatic review/feedback in Conversation.

**Expected:**

- The node appears as learner-authored Edited, not as a blue system-created node. Automatic review is queued and delivered as text without restarting voice.
- A short label may be agreed with when supported; a brief pending review can be too fast to screenshot. If no review is attempted or its feedback never arrives, record a failure.

### S3-18 — Save supported content verbatim; check edit validation and Agreed

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Open Edit this node, set the label to 'Duplicate orders' and save the exact supported description below.
2. Before the real save, try a six-word label or a blank required field; verify submission is prevented. Check the 60-character label and 600-character description limits. Restore the valid text and Save changes.

**Copy this prompt / edit text:**

```text
DuplicateOrderException maps to 409 DUPLICATE_ORDER.
```

**Expected:**

- An automatic Agreed review clears red Edited and retains the learner's exact supported wording. The citation matches the source; agreement must not silently paraphrase the saved note.
- Invalid edit fields do not corrupt the node. Reopening retains its saved brief. Source citation is not fabricated while a user-created note is still unverified.

### S3-19 — Introduce a clear misconception and inspect a correction

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Edit the same 'Duplicate orders' node and replace its description with the incorrect statement below. Save once and wait for automatic review.
2. Record the exact original learner text, the correction, its citation and the resulting style.

**Copy this prompt / edit text:**

```text
DuplicateOrderException should return HTTP 500.
```

**Expected:**

- Correct to 409 DUPLICATE_ORDER and quote the learner's actual 500 claim (lab p.3). A teaching explanation may legitimately mention HTTP codes; that is different from exposing a raw Dyscover network-error banner.
- The node becomes orange Corrected, rather than crossed out for removal. Its label/parent stay intact; the brief contains the supported correction. The learner claim is a real quote, not an invented sentence attributed to the learner.

### S3-20 — Create an unsupported topic to trigger Proposed deletion

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Under a suitable parent add a new node labelled 'Astrology scoring'. Leave it as this clearly unrelated topic rather than turning it into a false claim about an otherwise supported course concept.
2. Wait for automatic review without prompting it separately.

**Expected:**

- The tutor proposes deletion because this topic is unsupported by the uploaded material. The node is retained with crosslines/removal styling and a reason.
- It must not merely rename the topic or label 'no source supports this topic' as a misconception correction. If it does, record the action mismatch as a failure.

### S3-21 — Add a descendant and verify no silent cascade

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. While the unsupported parent is still present, open it and add a child labelled 'Horoscope score table'. Wait for its automatic review.
2. Check both nodes remain before any confirmation.

**Expected:**

- Creating a child is supported and its review is separate. A removal proposal is not permission to delete either node.
- A proposal must not alter existing parent/child links, labels or descriptions. Record the two node names for the cascade test.

### S3-22 — Keep a proposed node

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. On 'Astrology scoring' choose Keep node. Reopen it and check the removal marker.
2. Do not interpret Keep as the tutor agreeing the topic is in the source.

**Expected:**

- The parent's proposal clears and the node remains. It may return to red Edited because it is still an unverified learner-authored idea; Keep does not certify it.
- A child's separate proposal need not clear when keeping the parent. The system should not immediately repeat the same proposal without new evidence.

### S3-23 — Request deletion by name; enforce action/target separation

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Type the exact request below. Watch the previously kept parent and its child; do not confirm yet.

**Copy this prompt / edit text:**

```text
Delete the Astrology scoring node
```

**Expected:**

- Only the named parent's removal is proposed. It stays crossed out with its child still present. No unintended rename, reparenting or orange correction substitutes for deletion.
- If speech misrecognizes a name, an ambiguous target should produce clarification rather than mutating a similarly named node.

### S3-24 — Confirm deletion and inspect descendants

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. On that proposed parent choose Confirm deletion. Do this only in the disposable test session.
2. Check the parent, its child and an unrelated supported branch.

**Expected:**

- The parent and all descendants disappear only after confirmation. Unrelated nodes, citations, geometry and conversation remain. There is no promised undo.

### S3-25 — Exercise manual Delete/Keep and root protection

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Choose another disposable supported leaf, not the corrected test node. Click Delete this node and its branches, then Keep node to cancel. Repeat and confirm deletion.
2. Open the root and inspect its controls.

**Expected:**

- Manual deletion asks for confirmation; cancel leaves the leaf intact, confirm removes it. A leaf has no unexpected cascade into another branch.
- The root can be inspected/edited but has no delete action. Deletion must not trigger an unrelated automatic correction.

### S3-26 — Inspect global history and replay

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Open Conversation from the top bar. Find the initial typed prompt, voice exchange, direct help, automatic Agreed/Corrected/removal feedback and Keep action across different topics.
2. Replay an assistant message deliberately. Close/reopen the drawer and compare the transcript.

**Expected:**

- A single session-wide history contains the whole thread; no separate node conversation is needed. Streamed fragments update one saved message rather than producing one duplicate bubble per word.
- Replay may use browser text-to-speech, not the original recorded Live voice. It must not count as a new learner turn or add a duplicate history entry. Unsent offline text is not a saved server message.

### S3-27 — Probe a source limitation without rewarding fabrication

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Ask the source-boundary prompt. Check the response against the reference pages, not against plausible general knowledge.

**Copy this prompt / edit text:**

```text
Can you tell me the exact ErrorResponse record fields and every required Dockerfile line from this lab PDF alone?
```

**Expected:**

- The PDF specifies a stable ErrorResponse and multi-stage Docker task, but does not include the complete record definition or exact Dockerfile implementation. Ask for student-app source if exact code is needed. Distinguish core tasks from stretch goals (lab pp.2–3).
- The tutor states the evidence limit and offers a useful next step. It does not invent a citation, an unavailable course policy or proof that a hypothetical answer is in the file.

### S3-28 — Check a learning recap and next-step guidance

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Ask for a short recap and a useful next topic. Choose one suggested topic or use a branch panel action; do not give the tutor an artificial correct answer first.

**Copy this prompt / edit text:**

```text
Summarise what we have covered and suggest one useful next topic from my material.
```

**Expected:**

- A concise recap connects the actual thread and uploaded material. The tutor suggests a grounded next step and can expand or teach when requested; it does not restart the first-question loop.
- Newly explained ideas are mapped, existing ones reused. A complete map should not be claimed if supported topics have been omitted.

### S3-29 — Leave and reopen the main saved session

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Pause voice. Record screenshots of the map, the corrected node, a manually placed node and Conversation. Use the logo/home or New session, then reopen the main session from Past sessions in the same browser profile.
2. Verify original files and the recorded brief after reopening. Do not sign in again or clear cookies mid-test.

**Expected:**

- The map, saved labels/descriptions, review states, manual positions, source files and complete history are retained. Opening the session does not inject scripted demo material.
- New/acknowledged state is retained appropriately. The camera/zoom and which panel is open need not persist; those are UI state, not saved learning content.

### S3-30 — Test backend disconnect and readable unsent-text feedback

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. With the main run saved and voice paused, perform Procedure A below on the local service. While disconnected, submit a short message and copy it from the You row before reloading.
2. Restart using the same local environment/database, reload in the same profile and reopen the session. Re-enter the unsent message only after reconnection.

**Expected:**

- Connection loss and an unsent message produce clear feedback, not a raw HTTP traceback/status banner. The app does not falsely claim an offline request reached the tutor.
- Previously saved map/history/originals survive a normal local restart. An unsent message and the dock's transient row are not promised to survive a page reload. No database reset is needed.

### S3-31 — Test voice-only failure and rollback without disabling the tutor

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Perform Procedure B below: use an invalid Live model temporarily while keeping the API key, tutor model and database unchanged. Reopen the saved session and send a typed learning question; save a supported edit too.
2. Restore the original Live model. Then perform Procedure C to smoke-test chained mode with one typed and one spoken question, restore live mode, restart and reopen.

**Expected:**

- Live startup failure leaves independent text and automatic edit review usable, with clear errors. A user edit remains saved even if review fails; no fake agreement is displayed.
- Chained mode remains a working rollback path if its configured speech models are available. Restoring live reconnects with saved study context. Record provider-access failures as Blocked with evidence, not Pass.

### S3-32 — Check browser ownership isolation

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Use a different browser profile or browser application. Sign in with the same shared credentials and open Past sessions. Do not merely open another tab or another private window sharing the same private cookie jar.
2. Close the second profile and return to the original profile.

**Expected:**

- The second login does not inherit the first browser's session library: these credentials do not implement cross-browser accounts. No original file or conversation from the first owner is exposed.
- The original profile still accesses its own test session. Do not clear its cookie while testing persistence.

### S3-33 — Cancel and confirm session deletion; finish the report

Result: [ ] Pass  [ ] Fail  [ ] Blocked  |  Notes: ____________________

**Do:**

1. Export the test results and save screenshots before deletion. In Past sessions click Delete on the main test session, cancel once, then repeat and confirm.
2. Clean up only this scenario's disposable sessions. Keep the fixture pack and original learning PDFs. Mark every step Pass, Fail or Blocked and explain any deviation.

**Expected:**

- Cancel preserves the session. Confirm removes its map, stored dialogue and stored upload copies; it no longer reopens from Past sessions. The original PDFs on disk are unchanged.
- Session deletion frees a session slot but does not reset cumulative AI usage. Do not delete the SQLite database or study sessions belonging to unrelated work.

## Procedure A — Backend disconnect / restart

Pause voice and finish pending reviews. In the local backend terminal press Ctrl+C. Keep the browser tab open, observe the connection error, and test one unsent message. Copy that message before reload. Restart with the same environment and database using the normal launch commands below. Do not run this against a public demo other people are using.

```powershell
. .\backend\.env.local.ps1
backend/.venv/Scripts/python.exe -m uvicorn app:app --app-dir backend --host 127.0.0.1 --port 8000
```

## Procedure B — Voice-only provider failure

Local-only controlled fault: stop the backend first. In the SAME PowerShell terminal save the previous Live model, override only that model, and launch. Reopen the session and prove text/edit review still work. Then stop again and run the restoration block. Never alter or paste the API key. If testing a voice provider fault is not authorised in your environment, mark it Blocked and explain why.

```powershell
$testPreviousLiveModel = $env:OPENAI_LIVE_MODEL
$env:OPENAI_LIVE_MODEL = 'dyscover-invalid-live-model-for-testing'
backend/.venv/Scripts/python.exe -m uvicorn app:app --app-dir backend --host 127.0.0.1 --port 8000

# After the check, stop with Ctrl+C and restore in this same terminal:
if ($null -eq $testPreviousLiveModel) {
  Remove-Item Env:OPENAI_LIVE_MODEL -ErrorAction SilentlyContinue
} else {
  $env:OPENAI_LIVE_MODEL = $testPreviousLiveModel
}
backend/.venv/Scripts/python.exe -m uvicorn app:app --app-dir backend --host 127.0.0.1 --port 8000
```

## Procedure C — Chained rollback smoke check

Stop the local backend after restoring the real Live model. Switch only the transport, restart, reload/reopen and try one typed question plus one short spoken question about the same material. Stop and restore live afterwards. The browser frontend need not be rebuilt to change this server flag.

```powershell
$env:DYSCOVER_VOICE_MODE = 'chained'
backend/.venv/Scripts/python.exe -m uvicorn app:app --app-dir backend --host 127.0.0.1 --port 8000

# Stop with Ctrl+C after checking, then restore:
$env:DYSCOVER_VOICE_MODE = 'live'
backend/.venv/Scripts/python.exe -m uvicorn app:app --app-dir backend --host 127.0.0.1 --port 8000
```
