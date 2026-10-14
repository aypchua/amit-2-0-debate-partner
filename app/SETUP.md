# PSC Singapore debate: "AI will replace us in the next 5 years"

Andrew argues the Proposition, solo, with an AI teammate ("AMIT 2.0") that listens to the opposition and
puts rebuttals on screen within ~2 seconds. Andrew reads them aloud.

## Layout
- `app/` the teammate. Python 3.12 via `uv`. FastAPI server + single-page UI.
- `content/` scripts, cheat sheet, run of show, checklists. Print these.

## Run
```bash
cd app && ./run.sh
```
Run it from Terminal.app the first time so macOS attaches the microphone permission prompt to Terminal.
Opens http://127.0.0.1:8765.

## How it works
- **Speech-to-text:** Apple's on-device SpeechAnalyzer (macOS 26) through the `yap` CLI (`brew install yap`).
  Streams a phrase per line while they talk. "System audio" mode needs Screen Recording permission; use it to
  rehearse against `say -f content/99-mock-opposition-speech.txt`.
- **LLM race:** every provider in `app/providers.json` with a key in `app/.env` fires at once; the first to
  produce a token wins and streams, the rest are cancelled. The local Ollama model always races too, so no
  Wi-Fi still lands a rebuttal (~2-3s).
- **Running notes:** while listening, provisional bullets refresh every ~25s so nothing is cold at the end.

## Facts the model may cite
`app/prompts/facts.md` is the ONLY source of numbers the model is allowed to use; anything else with a statistic is a
hallucination and you cut it live. The full list with URLs and who verified each row is `content/07-facts-bank.md`.
Add a fact there only after opening the source yourself, then copy a one-line version into `facts.md` and restart.

## Keys
Copy `app/.env.example` to `app/.env` and fill in whichever you have. Free tiers exist for Cerebras and Groq.
No keys = local only, which already works.

## Adversarial training loop
`app/adversarial/suites/*.json` hold opposition speeches (the real playbook is suite 01). `uv run python adversarial/run.py
adversarial/suites/<file>.json` drives the live server through the whole debate (slots, memory, summary mode) and writes a
report to `app/adversarial/out/`. Read it, note what AMIT missed or invented, add the counter to `app/prompts/counters.md` (one `### Playbook` section per
opposition angle; the two sections whose vocabulary best matches the live transcript are injected per request, so the
prompt stays short) or the fact to `app/prompts/facts.md`, restart, rerun. General flips live in `system.md`. Three passes on suite 01
took the rebuttal from 5/10 to usable.

## Racers
The local model is the preferred racer (`head_start_ms` in providers.json): it follows the rules far better than
gpt-oss on Cerebras/Groq and wrote the best passage in every comparison. Cloud is adopted only if local has no first
token within 2.5 s. Running notes are local-only, which keeps its cache primed so the real STOP is usually under 0.5 s.
Free-tier Groq rate-limits after heavy testing (HTTP 429); harmless on the night, but do not run suites on the same key
in the hour before the event.

## Racers and priority (Sept 10)
`providers.json` gives each racer a `priority`. When the first token arrives from anyone, the race waits up to
`grace_ms` (2.5 s) for higher-priority racers and reads the best one that has started. Current order: Claude Sonnet 5
(thinking off) > local Qwen 3.6 > Cerebras Qwen 3.8 (reasoning off). Local always races, so a Wi-Fi failure costs speed,
not the rebuttal. Groq and gpt-oss are disabled: fast but they ignore the rules. Model bake-off with automatic
compliance scoring: `uv run python adversarial/model_bakeoff.py adversarial/candidates-round2.json 3`.

## Guardrail
After each passage the server checks for forbidden tic words (cathedral, fortress, pillars, "built a", the name Andrew)
and for six-word overlaps with anything already said tonight. On a hit it rewrites once with the problem named; the UI
shows "rewriting" for the few seconds it takes. Debate memory keeps full opposition transcripts but only markers plus
closing lines for our own passages, because the model copied its own earlier openings when it saw them in full.

## Bake-off (pick racers on wit, not speed)
```bash
cd app && uv run python bench.py 2
```
Score `app/bench_out/blind.md` 1-5 per output, then look at `key.md`. Set `enabled: false` on the losers.

## Live-written speeches (Sept 10)
Space writes the WHOLE second speech (mode `speech2`, ~5 min) from the opposition transcript plus the ideas in
`content/03-second-proposition.md`; STOP & WRITE SUMMARY writes the whole summary (mode `summary`, ~3 min) from both
speeches, what Amit already said, and `content/04-rebuttal-summary.md`. Long passages page at ~120 words in big type.
The guardrail cannot rewrite a speech being read, so for these modes it edits in place: scrubs tic words and removes
any sentence with an unverified percentage, flagging it in the pane header. Script 1 shows the scripted first speech.

## Show mode (retired; still available with S)
Press S. A run-of-show rail lists the six slots; arrow keys move between them. Your slots show the script from
`content/` as a teleprompter with Amit's passage inline at the `[[AMIT]]` marker. Opposition slots start the mic and
show transcript, notes and rebuttal. Debate memory archives each opposition speech and every Amit passage; the summary
slot sees all of it. Outside Show mode the same memory fills when you press Clear (archive, not discard), and the
Summary button generates the closing passage from it. Reset (with confirm) wipes memory for a new debate; Clear never does.

## Keyboard
Space = STOP & REBUT (summary in slots 4 and 6). S = Show mode. Left/Right = slots. Tab = full-screen rebuttal. L = Listen. P = Panic lines. Enter in the Ask box.
