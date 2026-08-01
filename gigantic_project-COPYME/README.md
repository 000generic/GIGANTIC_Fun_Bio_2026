<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 25
Human:   Eric Edsinger
Purpose: User-facing project landing page for any renamed gigantic_project-*
         directory. Establishes the project as research-grade, covers
         orientation, and lays out the Human-AI Chat Provenance system
         (the chat-as-research-notebook feature).
Scope:   The renamed gigantic_project-* directory and its contents.
History:
  2026-05-25  Initial scaffold (Opus 4.7). Contains the locked-in Human-AI
              Chat Provenance section. Remaining sections (quick start,
              subprojects overview, conventions summary) to be filled as
              the documentation cleanup pass progresses through subprojects.
============================================================================ -->

# Your GIGANTIC Project

You are looking at a `gigantic_project-*` directory — your renamed copy of
the GIGANTIC project template. Everything for your research project lives
here: inputs, subprojects, workflows, outputs, and the complete record of
how the work was done.

The mantra: **you guide AI - AI does the work!** That includes the
documentation work. This project is set up so that every AI chat session
becomes part of your scientific record automatically.

---

## Human–AI Chat Provenance

**Every AI chat session you run in this project is captured as a research
artifact.** This is one of GIGANTIC's primary features. The chat history
itself — the conversation that shaped each decision, ran each command,
produced each result — is preserved alongside the code and the data.
Think of it as a lab notebook for AI-driven research, running
automatically in the background.

### What gets captured, where, and how

When you use **Claude Code** in this project, the full session transcript
is automatically gzipped and saved before each context compaction:

```
research_notebook/research_ai/sessions/
├── YYYYMMDD_HHMMSS-claude_code-MODEL-SESSION_ID.jsonl.gz   ← your captured sessions
├── TRANSCRIPT_CAPTURE_LOG.md                               ← human-readable index
```

Each `.jsonl.gz` is the **complete, lossless record** of one session
segment — every message, tool call, file read, and command result. Nothing
is summarized; nothing is dropped. Disk footprint grows over the life of
the project, and that is by design.

### "Save Chat!" — on-demand capture

At any meaningful moment, type **"Save Chat!"** in your chat. Your AI
will trigger an on-demand capture of the current session and any other
recent Claude Code sessions for this project.

Good times to say "Save Chat!":

- Just finished a significant milestone or made an important decision
- Wrapping up for the day or about to close your laptop
- Periodically during a long, productive session
- Anytime it feels like "I should make sure this is recorded"

Your AI should also proactively suggest "Save Chat!" when it senses one
of these moments. If your AI isn't doing that, ask it to.

### These captures are originals — **never edit them**

Treat `research_notebook/research_ai/sessions/` like the original pages of
a research notebook: **read-only, permanent, complete**. Do not edit
captured transcripts. Do not delete them. Do not "clean them up". They are
the canonical scientific record of how the work was done.

If a particular captured session contained frank language, unflattering
references to collaborators, draft hypotheses you're not ready to share,
or commands that leaked credentials — that's fine, and expected. The
originals stay as they are.

### For publication: make copies, scrub the copies

When you want to share captured chat content as part of a publication
(journal supplementary materials, an archive, a methods paper appendix),
**make copies first**, scrub the copies for whatever needs to be removed,
and publish the cleaned copies. The originals in
`research_notebook/research_ai/sessions/` stay untouched.

Your AI can help walk you through what to scrub: collaborator names in
unflattering context, leaked credentials, internal lab politics, draft
hypotheses, frustrated language, anything else that doesn't belong in a
public artifact. The full step-by-step walkthrough (categories, output
format choices, the `SCRUB_NOTES.md` template) lives in
[`ai/ai_FYIs/publication_scrub_guide.md`](ai/ai_FYIs/publication_scrub_guide.md).
Read it (or ask your AI to read it) before starting a scrub.

Plan this work near the end of your project, when you know what you
actually want to publish.

### Other AIs work too — the principle is the same

If you use Cursor, ChatGPT/Codex, Gemini, or another AI assistant, the
capture system needs a small bit of setup specific to that AI (each one
stores session data differently). Concrete starting points (verified
May 2026; check your AI's current docs):

- **OpenAI Codex CLI**: sessions live at `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`
- **Gemini CLI**: use the built-in `/export jsonl` or `/export markdown` command
- **Cursor IDE**: storage at `~/.cursor/projects/` plus a SQLite file
- **Cursor CLI**: `~/.cursor/chats/`
- **ChatGPT web UI**: manual export per conversation

Your AI can walk you through the setup on first use — ask it to read
`AI_GUIDE.md` in this directory (the table there has more detail) and
help you wire up an equivalent capture script in `ai/ai_scripts/`. The
principle is identical regardless of AI: lossless, permanent,
never-edited captures landing in `research_notebook/research_ai/sessions/`.

### Why this matters

For AI-assisted research to be acceptable in fields like phylogenomics,
the AI cannot be a black box. Every action it takes, every decision it
proposes, every result it interprets needs to be traceable. Captured
chat sessions are that trace — the scientific equivalent of a complete
lab notebook with hand-written entries, retained for the entire project
and beyond. They turn AI assistance into AI collaboration with a
permanent record.

---

## (Remaining sections — to be filled as the documentation cleanup pass progresses)

- Quick start: getting your data into `INPUT_user/` and starting work
- Project layout: subprojects, workflows, conventions
- Where to ask your AI for help
- How to share your project (or pieces of it)

*These will be filled in as we cover each layer during the documentation
cleanup pass. The Human–AI Chat Provenance section above is locked in and
will not change substantively as the rest is authored.*

---

## Session hygiene (per §61 in `ai/ai_FYIs/gigantic_conventions.md`)

GIGANTIC's chat-as-research-notebook convention (§9) works best with
disciplined session hygiene. Two recommendations.

### Always root at the named gigantic_project-COPYME

Every chat session for project work should be initiated rooted at the
user's renamed copy of `gigantic_project-COPYME/` — e.g.,
`gigantic_project-cephalopod_evolution/`.

**Not** at:
- `GIGANTIC/` (the framework root, reserved for framework-development
  sessions per §16)
- `subprojects/<X>/` (a subproject directory)
- `subprojects/<X>/<BLOCK_or_STEP>/workflow-COPYME-*/` (a workflow directory)
- Any other directory deeper than the named project root

Why: the renamed project copy is the canonical session root. All
project conventions, INPUT_user paths, research_notebook captures,
and AI guidance are scoped to that directory. Rooting deeper than
that scopes the AI's view too narrowly and loses cross-subproject
context (and the AI guides at lower levels assume the session was
rooted above them). Rooting at `GIGANTIC/` is reserved for
framework-development sessions per §16.

### One chat session per subproject + a side channel for small questions

For productive project work:

- **One session per subproject** you're actively working in. A session
  focused on `phylonames/` is different from one focused on
  `genomesDB/` is different from one focused on `trees_species/` —
  each maintains its own context, convention reminders, and recent
  state.
- **Continue the same session over many compactions** until it
  becomes overly reactive, muddled, or slow. Compactions are
  lossless (per §9 the full transcript is captured), so a long
  session isn't a problem until it starts feeling like one.
- **When a session goes muddled, start a fresh one** at the same
  named `gigantic_project-*/` root, focused on the same subproject,
  and bring it back up to speed (read the relevant AI_GUIDEs, recent
  commits, etc.).
- **Keep a separate "small questions" session** for random or
  cross-cutting questions (e.g., "what does this convention mean?"
  or "is this NCBI accession a GCF or GCA?"). This keeps the
  subproject sessions focused on their actual work and prevents
  context pollution.

### What this prevents

- Sessions that try to hold every subproject's state in context and
  end up confused about which one they're operating on.
- Sessions that get derailed by one-off questions and lose their
  thread on the subproject work.
- Session captures (per §9) that mix multiple unrelated subprojects
  into a single transcript, making the lab-notebook record harder
  to grep later.
