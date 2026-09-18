# PB158 · Lecture 2 — I/O from Python to the operating system

*Faculty of Informatics, Masaryk University (FI MUNI) · 2026-09-15*

Every I/O call you write sits several layers above the operating system, and the layers are observable.

## What is in this archive

| file | what it is |
|---|---|
| `2026-09-15-pb158-lecture-2-io-from-python-to-the-os-slides.pdf` | the deck, one page per slide |
| `2026-09-15-pb158-lecture-2-io-from-python-to-the-os-handout.pdf` | the written version, with every source and a one-page summary of each one |
| `2026-09-15-pb158-lecture-2-io-from-python-to-the-os-speaker-notes.pdf` | the notes the talk was given from |
| `index.html` | the deck as a web page — open it in a browser, it works offline |
| `AGENTS.md`, `CLAUDE.md` | instructions for an AI coding agent, see below |
| `demo/` | Sections 4 and 5 demo — one program, two jobs — see its own `README.md` |

## Reading it

Start with the slides if you were in the room and want the argument back.
Start with the **handout** if you were not: it is the deck's claims written out,
and every claim carries a numbered source.

Two kinds of source appear:

- **`[S1]`, `[S2]`…** — external. A paper, a vendor document, a post. The
  handout gives the URL.
- **`[V1]`, `[V2]`…** — a note from the speaker's own working vault, which is
  not public. You cannot follow those links, so the handout carries a one-page
  summary of each one instead, along with every external reference that note
  itself cites. Nothing is hidden behind a citation you cannot reach.

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

Ondřej (Ondra) Krajíček in Czech contexts, Ondrej (Ondra) Krajicek in international ones — me@ondrejkrajicek.com · https://linkedin.com/in/OndrejKrajicek
