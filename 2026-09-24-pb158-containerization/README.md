# PB158 — Containerization



A container is not a lightweight virtual machine: it is an ordinary process that Linux kernel mechanisms isolate.

Edition: v5 · 37b395f62 · built 2026-09-30

## What is in this archive

| file | what it is |
|---|---|
| `2026-09-24-pb158-containerization-slides.pdf` | the deck, one page per slide |
| `2026-09-24-pb158-containerization-references.pdf` | every source the talk cites, and a one-page summary of each vault note |
| `references.html` | the same references as a web page |
| `2026-09-24-pb158-containerization-speaker-notes.pdf` | the notes the talk was given from |
| `index.html` | the deck as a web page — open it in a browser, it works offline |
| `AGENTS.md`, `CLAUDE.md` | instructions for an AI coding agent, see below |
| `demo/` | files that ship with the talk — see its own `README.md` |

## Reading it

Start with the slides if you were in the room and want the argument back.
The **references** document (`2026-09-24-pb158-containerization-references.pdf`) resolves every numbered
source the slides carry.

The edition line at the top names the build: the edition number, the commit it
was built from and the build date. The cover slide, every PDF and these files
carry the same line, so quote it when you ask about something in here.

Two kinds of source appear:

- **`[S1]`, `[S2]`…** — external. A paper, a vendor document, a post. The
  references document gives the URL.
- **`[V1]`, `[V2]`…** — a note from the speaker's own working vault, which is
  not public. You cannot follow those links, so the references document
  (`2026-09-24-pb158-containerization-references.pdf`) carries a one-page summary of each one instead,
  along with every external reference that note itself cites. Nothing is hidden
  behind a citation you cannot reach.

## Asking questions about it

This archive is set up to be read by an AI coding agent. Unzip it, open a
terminal in the folder, and run `claude` or `codex`. The agent reads
`CLAUDE.md` or `AGENTS.md` automatically and will know what these files are and
how to answer from them.

Ask it things like *"what is the evidence for the claim about verifier
independence?"* or *"summarise what section 3 argues and what it does not
claim"*. It has been told to answer from these documents and to say when they
do not settle a question, rather than filling the gap.

---

Ondrej (Ondra) Krajicek — me@ondrejkrajicek.com · https://linkedin.com/in/OndrejKrajicek
