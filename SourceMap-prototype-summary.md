# SourceMap prototype: main ideas and evidence

**Idea:** A study tool for dyslexic college learners that turns their own lecture notes or readings into a small, editable diagram, then uses that diagram for recall practice.

## Requirements background: learning difficulties to address

The following figures come from a 2025 British Dyslexia Association survey of **500 dyslexic young people aged 13–18**. They describe the surveyed group, not every dyslexic learner or a separate further education college sample. [Local BDA report](<references/BDA-Report_Set-up-for-somebody-else-report_Oct-2025.pdf>)

- **Reading and spelling:** 76% reported difficulty with reading and 77% with spelling. **Requirement:** let learners find the main ideas without first having to work through every paragraph, while keeping the original material available.
- **Writing:** 69% reported difficulty with writing. **Requirement:** allow spoken or short-text explanations and natural-language diagram edits, with no need to produce a long written response to use the tool.
- **Remembering and organising:** 45% reported difficulty remembering things and 45% organising themselves. **Requirement:** show how ideas connect in a manageable diagram and offer short, repeatable recall exercises.
- **Tests and exams:** 85% felt that dyslexia made tests and exams hard for them. **Requirement:** provide low-pressure practice that reveals what the learner can recall and where to review the source.

These requirements are hypotheses for the prototype. Interviews and usability tests with the intended college-age users should determine which difficulties matter most in their real coursework.
## What the prototype should achieve

- **Turn a short lesson into a clear diagram.** The learner uploads or pastes material and asks a focused question. The tool shows the main ideas and their relationships as a simple flowchart, timeline or concept map. Research suggests diagrams alongside text can improve recall, although this has not yet been established for this particular tool or audience. [Diagram and recall study](<references/Diagram and recall study.url>)

- **Keep every diagram connected to its source.** Selecting an idea or arrow shows the passage or slide it came from. The learner can check the explanation and spot mistakes. This matters because research on AI-generated educational diagrams has found factual errors, especially with complex inputs. [Educational diagram generation study](<references/AI educational diagram generation study.url>)

- **Let learners correct the diagram in everyday language.** For example: “Make this shorter”, “Move this step before that one”, or “Use the term from my lecture”. The change appears as a preview that can be accepted or undone. This is a design proposal to test: research on post-secondary students shows that assistive tools do not automatically fit every learner's task, and training can affect how well tools are used. [UK post-secondary technology study](<references/UK post-secondary assistive technology study.url>)

- **Support active recall.** The tool hides a label or connection and asks the learner to remember or explain it, then shows feedback linked to the source. Retrieval-practice research gives a stronger basis for this than simply viewing a diagram repeatedly. [Retrieval practice and concept maps study](<references/Retrieval practice and concept maps study.url>)

- **Give learners control over detail and format.(customizatble)** Start with a few ideas, then let learners expand sections or return to the original text or audio. A study found that college students with dyslexia took longer to interpret more complex graphs, so diagram simplicity should be tested with users. There is no need to assume that every dyslexic learner has a single “visual learning style”. [Graph comprehension study](<references/Dyslexia graph comprehension study.url>) · [International Dyslexia Association on learning styles](<references/International Dyslexia Association learning styles.url>)

## One-minute demonstration

1. Paste a short lecture extract and ask, “How does this process work?”
2. Generate a five-to-eight-node diagram.
3. Click a node to see its source passage.
4. Type a correction and accept the previewed change.
5. Hide two labels and complete a short recall exercise.



