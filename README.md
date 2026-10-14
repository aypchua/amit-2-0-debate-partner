# AMIT 2.0: how a presales engineer vibe-coded his own debate partner

*Written up after the PreSales Collective APJ debate, September 2026. Motion: "AI will replace us in the next five years." Side assigned: proposition. Human teammate: unavailable. Replacement: this.*

## The problem

A fun, high-school-style debate, two speakers a side. My partner dropped out a few days before. The motion was literally about AI replacing presales people, so the obvious answer was also the funniest one: replace him with AI, and make the replacement the argument.

What that needed on the night:

- Listen to the opposition speak, live, in a meeting room with a table mic.
- The moment they sat down, write my next speech from what they had actually said.
- Put it on a screen fast enough that I could stand up and read it before the room got bored. Budget: under three seconds to the first words.
- Never invent a statistic. A made-up number in front of forty presales professionals ends the night.
- Keep working if the venue Wi-Fi died.

I am a presales engineer, not a software engineer. The whole thing was built in Claude Code over about three evenings, by describing what I wanted and reviewing what came back. This document is what we made and how.

## What got built

Everything lives in one small Python app plus a single HTML page, on a MacBook.

| Part | What it does | How it was chosen |
|---|---|---|
| Speech-to-text | Apple's on-device speech engine in macOS 26, driven through a small command-line tool called `yap`. Streams a finished sentence every second or two while the speaker is still talking. | A research pass compared Whisper variants, NVIDIA Parakeet, cloud services and the dictation apps I already had. Apple's engine was the only local option that streamed, needed no model download, and was trained for distant conference-table mics. The dictation app I assumed I would use only wrote text after the recording stopped. |
| The race | Three language models get the same prompt at the same time: Claude Sonnet 5 in the cloud, a local Qwen model on the laptop, and Qwen 3.8 on Cerebras. Whichever starts first gets read, with a 1.2-second grace window for a better-ranked one. The local model always runs, so no Wi-Fi means slower, not silent. | Measured, not guessed. A bake-off script scored every candidate on speed and on rule-following. The fastest models (gpt-oss on Cerebras and Groq) ignored the rules; the disciplined ones were kept. |
| The debate brain | A system prompt holding the motion, our definition of "replace", the seven-point case, a bank of about forty known opposition arguments with prepared flips, and a verified-facts list. | The counters bank grew every time the app lost a rehearsal. Everything in it maps to something the opposition actually said in a dry run. |
| Verified facts | A short file of statistics, each one checked at the source by a human. The model may cite only those, and must name the source in the same breath. | After the first rehearsal produced a confident "78% of buyers" that did not exist. |
| Guardrail | Code that checks each passage after it is written: forbidden tic words, wording repeated from earlier in the night, any percentage not in the facts file or the opposition's own words. Short passages are rewritten up to three times; long ones are edited in place because I am already reading them. | Prompt instructions alone did not stop the model saying "cathedral" four times a night or recycling its best zinger. Code did. |
| Debate memory | The server archives each opposition speech and remembers what the AI already said. The final summary sees both of their speeches, counts their concessions in their own words, and never repeats our earlier closing line. | Needed because a summary that only knows the last five minutes is not a summary. |
| Their numbers | While the opposition speaks, every percentage they say appears as a chip: green with the source if it matches our facts, orange with "ask: which report, which year?" if it does not. | For the night they brought their own AI, which skilled presales people obviously would. |
| The screen | Dark, huge type, one pane for the transcript and one for my speech, paged at about 120 words so there is never scrolling. Space stops the mic and writes the whole five-minute second speech; another button writes the whole three-minute summary. A latency counter in the corner, because the milliseconds are theatre. | The first version produced bullet points. Reading bullets aloud sounded like a robot, so it became spoken prose: short paragraphs, one anecdote, at most two facts, zinger last. |
| Paper backup | A 35-card printable deck: the scripted first speech, listen cards with tick-boxes for which argument they chose, six fallback rebuttals by angle, closing cards, cheat sheets and failure lines. | Because the laptop is the joke, and the joke must survive the laptop dying. |

## How it was trained without training anything

No fine-tuning. The model never changed. What changed was what it was told.

The opposition kindly shared their playbooks, six different angles from "accountability gap" to "put the motion on trial". Each became a test suite: a script pushes the three speeches through the live server exactly as they would arrive on the night, and writes out what the AI would have said. I read the output, noted what it missed or made up, added the missing counter or fact, and reran. Six passes on the real playbook took the rebuttal from "generic and dodging their best point" to turning their own study against them by name.

Things that only showed up by running it:

- Fast cloud models fabricated first-person anecdotes ("yesterday a CISO asked our portal...") and cited a hypothetical scene later as if it were evidence. The slower local model followed the rules. Discipline beat speed, so the race was re-ranked.
- Showing the model its own earlier passages made it copy them. Memory now stores only a marker and the closing line.
- Putting the counters in the system prompt kept the local model's cache warm and the first word under a second. Injecting them per request doubled the latency.
- A prepared second speech never matched the rebuttal, because it was written before the opposition spoke. So the app now writes the entire speech live, with my prepared ideas fed in as material to be rewritten around what they actually argued.

## Numbers from the night's setup

| Moment | Time to first word |
|---|---|
| Rebuttal after their first speaker, local model primed by running notes | about 0.3 seconds |
| Full five-minute second speech, Claude | 1 to 2.4 seconds |
| Full summary from both speeches | 1 to 2 seconds |
| Apple speech-to-text, last words after the speaker stops | under 1 second |

Cost of the cloud calls for the whole evening: well under one dollar.

## What vibe-coding actually looked like

- I described outcomes, not code: "the rebuttal pane needs no scrolling", "never let it say a number I have not checked", "what if they bring an AI too?"
- Claude Code did the research before recommending: which speech engines stream on a Mac, which models follow rules, what the Gartner figures really say. I pushed back when it assumed my installed tools were current. They were not.
- Every change was tested against real opposition material before I saw it, and reported honestly, including the runs that got worse.
- I rehearsed, told it what felt wrong (bullets sounded robotic, the prepared script did not tally, the elevator-operator joke appeared three times), and it fixed the cause rather than the symptom.
- Three evenings. Zero lines of code written by me. One joke, stolen by the laptop, that got the biggest laugh of the night.

## Setup and running

See [app/SETUP.md](app/SETUP.md) for installation, keys and the keyboard. Nothing works without your own API keys in `app/.env`; the local model alone is enough to run offline.

## Repo map

```
app/        server.py (FastAPI + SSE), llm.py (race, guardrail), stt.py (yap wrapper),
            prompts/ (system.md, counters.md, facts.md), static/index.html, providers.json,
            adversarial/ (opposition suites, runner, model bake-off)
content/    speeches, cheat sheet, facts bank with sources, run of show, cue-card deck
```
