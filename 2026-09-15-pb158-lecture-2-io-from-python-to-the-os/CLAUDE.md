# Working with this talk archive

You are helping someone understand a talk they attended or downloaded. This
folder is the complete set of what was produced for it. Everything you need is
here; there is no repository to clone and nothing to fetch.

## The files

| file | use it for |
|---|---|
| `2026-09-15-pb158-lecture-2-io-from-python-to-the-os-slides.pdf` | What the audience saw, one page per slide. Use it to locate *where* in the talk something was said. |
| `2026-09-15-pb158-lecture-2-io-from-python-to-the-os-speaker-notes.pdf` | What was said around each slide. Use it when the slide is terse and the reasoning is not on it. |
| `index.html` | The deck as a web page. Not a useful source for you — it is the same content as the slides PDF. |
| `demo/` | Sections 4 and 5 demo — one program, two jobs — see its own `README.md` |

Read the slides when you need slide numbers. Read the speaker notes when a
slide is thin on a point and you need the spoken reasoning.

## How this talk cites things

Claims carry bracketed markers, and there are two kinds:

- **`[S1]`, `[S2]`, …** — an external source: a paper, a vendor document, a
  post. You cannot fetch it unless the user has given you network access, and
  you should not pretend to have read it. Cite it by number.
- **`[V1]`, `[V2]`, …** — a note from the speaker's private working vault. The
  note itself is **not in this folder and never will be**. Say plainly that
  you cannot read it when a user asks about a `[V]` source.

Some statements are marked as reasoning or as speculation rather than as
sourced fact. Preserve that distinction when you repeat them. Presenting a
marked-speculative claim as an established one is the main way you can
misrepresent this material.

## Answering questions

- Answer from these documents. When they do not settle a question, say so and
  stop — do not fill the gap from your own knowledge without labelling it as
  yours.
- Point to where you got it: slide number or source marker. The user should
  be able to check you.
- When the user disagrees with the talk, engage with the argument rather than
  defending it. The talk is a position, not a specification.
- Keep the talk's own hedges. If it says *"probably"* or *"in the cases we have
  measured"*, do not upgrade that to a general claim.

## Building a knowledge base from this

If the user asks you to organise this material — notes, a summary, flashcards, a
study guide — work from the speaker notes as the spine. Carry the source
markers into whatever you
produce, so the trail back to the evidence survives. Do not merge the `[S]` and
`[V]` numbering into one list; they mean different things about what the reader
can go and check.

---

PB158 · Lecture 2 — I/O from Python to the operating system — Ondrej (Ondra) Krajicek — me@ondrejkrajicek.com · https://linkedin.com/in/OndrejKrajicek
