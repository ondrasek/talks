# PB158 · Lecture 3 — Finishing I/O, and advanced I/O

*Faculty of Informatics, Masaryk University (FI MUNI) · 2026-09-22*

Your program never talks to the disk, the network, or another program. It talks to the layer next to it — and every layer says done about something different.

## What is in this archive

| file | what it is |
|---|---|
| `2026-09-22-pb158-lecture-3-finishing-io-and-advanced-io-slides.pdf` | the deck, one page per slide |
| `2026-09-22-pb158-lecture-3-finishing-io-and-advanced-io-speaker-notes.pdf` | the notes the talk was given from |
| `index.html` | the deck as a web page — open it in a browser, it works offline |
| `AGENTS.md`, `CLAUDE.md` | instructions for an AI coding agent, see below |
| `demo/` | Lecture 3 demos — the Lecture 2 programs, plus whose done it was, and how a program waits — see its own `README.md` |

## Reading it

Start with the slides if you were in the room and want the argument back.
Every claim carries a numbered source.

Two kinds of source appear:

- **`[S1]`, `[S2]`…** — external. A paper, a vendor document, a post.
- **`[V1]`, `[V2]`…** — a note from the speaker's own working vault, which is
  not public. Nothing is hidden behind a citation you cannot reach.

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
