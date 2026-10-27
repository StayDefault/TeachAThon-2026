# Dyscover live demo script (about 3 minutes)

**Material:** Speech Processing, Module 3 "Digital Speech Signals", slides 16–26 plus the take-aways slide (12 pages: sampling, quantization, Nyquist frequency, aliasing).
**File to upload:** `/Users/kjmac/Documents/Edinburgh/Year3/Speech Processing/Lectures/03_digital_signals_DEMO_excerpt.pdf`
Do not commit this file: it is university course material. Citations will show excerpt page numbers, so excerpt page 7 = original slide 22.

**The loop to show:** the learner says what they think → the map changes with the discussion → the learner checks the source → the learner corrects the map.
**Also shown:** **Expand subtopics** grows a whole branch from the slides, and **Learn this topic** starts teaching any node with one click.

**Mode:** run in **live mode** (real backend + OpenAI). The bottom-left label must read **"AI-generated voice · Files sent to OpenAI"**. If you fall back to scripted mode, follow Plan C and say so out loud.

---

## 0. Setup (before the judges arrive, ~10 minutes)

1. Start the backend with a working key. On Mac:

   ```bash
   cd ~/Documents/Projects/TeachAThon-2026 && export OPENAI_API_KEY='…' DYSCOVER_TEST_EMAIL='demo@example.com' DYSCOVER_TEST_PASSWORD='…' DYSCOVER_SESSION_SECRET="$(openssl rand -hex 32)" DYSCOVER_MAX_AI_CALLS=5000 DYSCOVER_VOICE_MODE=live && backend/.venv/bin/python -m uvicorn app:app --app-dir backend --host 127.0.0.1 --port 8000
   ```

   If Live voice behaved poorly in rehearsal, use `DYSCOVER_VOICE_MODE=chained` instead (slower, but transcription and speech are separate steps).
2. Start the frontend in real mode: `cd Dyscover && VITE_USE_MOCK=false npm run dev`, then open http://localhost:5173 and sign in.
3. Check the bottom-left label: **AI-generated voice · Files sent to OpenAI**.
4. **Rehearse the full script at least twice** with this file. Keep the best rehearsal session: it is Plan B, available from **Past sessions**. Delete the other rehearsal sessions (the demo allows 30 saved sessions).
5. Allow the microphone. Use a headset or headphones: laptop speakers can feed the tutor's voice back into the mic.
6. Put the excerpt PDF on the desktop so it is easy to drag. Set browser zoom to 100%. Close other tabs. Turn on Do Not Disturb.
7. Agree on who drives the laptop and who narrates. The driver speaks the **learner** lines; the narrator speaks to the judges.

---

## 1. Script

| Time | What you do | What you say | What the judges should see |
|---|---|---|---|
| **0:00–0:15** Open | Drag the excerpt PDF onto the board, then click **Start studying**. | *Narrator:* "This is a real lecture from my Speech Processing course: twelve slides on how speech gets digitised. Dyscover is reading them now. Nothing here is scripted." | The file card flies into the study box. A root node appears and the tutor greets you. |
| **0:15–0:40** ① The learner asks a question | Voice mode is on. Ask by voice. | *Learner:* **"I don't really get the Nyquist frequency. Why does it matter when I record speech?"** | Live captions. The tutor explains from the slides, and nodes such as *Nyquist frequency* and *Aliasing* appear as it talks. |
| **0:40–1:05** ② The learner says what they think; the map changes | Say a deliberately wrong understanding by voice. | *Learner:* **"Okay, so if I record at 8000 hertz, I can capture sounds up to 8000 hertz. Is that right?"** | The tutor says "not quite": only up to 4000 Hz, half the sampling rate. A node turns **orange, CORRECTED**, quoting *You said: "…up to 8000 hertz"*. |
| | | *Narrator:* "It put my exact words on the map next to the correction, so I can see where my thinking went off." | |
| **1:05–1:25** ③ Check the source | Click the orange node, or the *Nyquist frequency* node. | *Narrator:* "Why trust the AI? Every node links back to my own slides." | The side panel shows **FROM YOUR MATERIAL** with the highlighted quote "Frequencies above half the sampling rate (the Nyquist Frequency)…" and a link to the excerpt PDF at page 7. |
| **1:25–1:45** ④ The learner corrects a node | Close the panel. Say it by voice, using the label the node actually has on screen. | *Learner:* **"The slide defines it exactly. Can you rename the Nyquist frequency node to 'Nyquist: half sampling rate'?"** | The tutor confirms, and only that node's label changes. |
| **1:45–2:10** ⑤ Expand subtopics | Click the dark **root** node. In the panel, click **Expand subtopics**. | *Narrator:* "So far the map follows our conversation. If I want the whole picture, I ask it to expand a topic from the slides." | The panel shows "Expanding subtopics…". Several new child nodes, such as *Sampling rate*, *Quantization* and *Bit depth*, appear under the root in one go. The tutor summarises them in two sentences, and the panel lists them under "Choose a subtopic to inspect, expand, or learn." |
| **2:10–2:35** ⑥ Learn this topic | In that list, click **Quantization** (or the closest new subtopic). Then click **Learn this topic**. | *Narrator:* "Clicking a subtopic only opens it. Nothing happens until I choose. Now I ask it to teach me this one." | The panel shows "Preparing explanation…". The tutor explains quantization from the slides in plain language ("the number of bits sets how many amplitude levels…; 16 bits is usually enough") and invites you to say it back. |
| **2:35–2:55** ⑦ Text input closes the loop | Click the **keyboard** button at the left of the dock and type: | *Learner types:* **"So more bits gives more amplitude levels, so the wave is stored more precisely, and 16 bits is usually enough."** | The submitted text stays visible in the dock. The tutor confirms, and *Quantization* turns **green with ✓ and the learner's own words quoted**. |
| | | *Narrator:* "Typing works the same way, for a noisy room or for anyone who'd rather not speak. The green card is my understanding, in my words." | |
| **2:55–3:10** Close | Point at the map. | *Narrator:* "So: I say what I think, the map changes with the conversation, I check it against my own slides, and I correct it. When I want more, I expand a topic or ask it to teach me, one click each." | The whole map: white, orange and green nodes, with the expanded branch. |

**If you must finish by 3:00:** drop the narrator line in ② and shorten the close to its first sentence. If you're still long, drop ④; ⑤, ⑥ and ⑦ are new and more visual. Never cut ①, ②, ③ or ⑦.

**While the tutor is thinking** (each turn can take a few seconds; Expand takes the longest), fill the gap with the narrator lines. Don't click anything while the status says "Thinking…", "Expanding subtopics…" or "Preparing explanation…". Expand and Learn are disabled until the tutor answers.

---

## 1b. Function test: Expand subtopics and Learn this topic (run before the demo)

Run these on a fresh session with the same PDF. Mark each pass or fail. If something fails twice, take that beat out of the live demo and keep it for Q&A.

| # | Do | Pass when |
|---|---|---|
| E1 | Open the root node, then click **Expand subtopics**. | The status reads "Expanding subtopics…" and both buttons are disabled. Within about 20 seconds, several children appear under the root in one batch. The panel then shows the root with the new children listed. |
| E2 | Open a new child and check its source. | It has **FROM YOUR MATERIAL** with a real quote from the excerpt. No child is about something that isn't in the 12 slides. |
| E3 | Click **Expand subtopics** on the root again. | No duplicate children appear. Either it adds genuinely missing topics, or the tutor says the slides are already covered. |
| E4 | Open a child, then click **Expand subtopics** on it. | New grandchildren appear only under that child. Existing nodes keep their labels and positions, including ones you dragged. |
| E5 | Click a child's name in the panel's subtopic list. | That child's panel opens and the tutor stays silent. Selecting a subtopic must never start a turn. |
| L1 | Open *Quantization* (or any child), then click **Learn this topic**. | The status reads "Preparing explanation…". The tutor explains that topic, not another one, from the slides, in short sentences, and invites you to explain it back. **Conversation** shows the request as "Teach me about Quantization." |
| L2 | After L1, say or type a correct explanation in your own words. | The node turns **green ✓** with your words quoted. The tutor moves on and doesn't ask the same question again. |
| L3 | After L1, say "I don't know" twice. | The tutor gives the answer briefly and moves on. The node is marked **Review**, and it doesn't loop on the same question. |
| L4 | Click **Learn this topic** on a node, then immediately try clicking it again. | The second click does nothing while the first is in progress. |

Record which node labels the model produced in rehearsal. They are usually similar from run to run, which tells you which child to click in ⑥.

---

## 2. Backup plans

| Problem | What to do |
|---|---|
| The tutor answers ② correctly but no node turns orange | Keep going. The correction is still in the captions. Say: "It corrected me out loud." Then click the *Nyquist* node in ③ as planned. |
| The node labels differ from the script | Use whatever label is on screen in ③, ④ and ⑥, e.g. "rename the *Sampling and aliasing* node to …". The labels come from the model, so they change from run to run. |
| **Expand subtopics** adds nothing, or only one node | Say: "The slides on this branch are already covered." Then click **Learn this topic** on an existing node and carry on with ⑥. |
| **Learn this topic** explains a different topic, or takes too long | Say the request out loud instead: "Teach me about quantization." Same effect, by voice. |
| Speech is misheard | Say "Let me type it" and switch to the keyboard. This also covers ⑤ early. The tutor matches sound-alike names, so "face" can still find "Phase". |
| A turn errors or takes more than about 20 seconds | **Plan B:** open **Past sessions**, open the rehearsal session, and continue from ③ on that map. Say: "Here's the same material from our rehearsal a few minutes ago." |
| The API, network or key fails entirely | **Plan C (scripted mode):** run `cd Dyscover && VITE_USE_MOCK=true npm run dev`, open it, click **Use demo files → Start studying**, and say exactly: **"We've switched to our scripted demo mode. You can see the label 'Demo mode · scripted backend' at the bottom. It plays a fixed lesson on backpropagation and does not analyse uploaded files, but it shows the same interaction."** |
| Echo: the tutor interrupts itself | Use headphones, or pause voice (tap the dock) and continue in text mode. |

---

## 3. Notes for the Q&A

- **Is it really reading our file?** In live mode, yes. Every node cites a passage from the uploaded PDF; open a node to show it. The scripted mode is clearly labelled and only replays a fixed story.
- **What stops the AI inventing things?** A server check runs on every node: it must cite a real passage from the upload. A correction must quote what the learner actually said. Removal always waits for the learner's confirmation.
- **Why a map and not a chat?** Dyslexic learners can keep the structure on screen instead of in working memory. They can hear and speak instead of reading and writing, and see their own words when they've got it right.
- **What it isn't yet:** not evaluated with learners, and no spaced review between sessions yet. Our evaluation harness (`backend/evals/run.py`) measures question loops, progress and grounding on course materials.
