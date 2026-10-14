# Day-of checklist

## The night before
- [ ] `cd app && ./run.sh` once from **Terminal.app**; grant the mic permission prompt to Terminal when it appears.
- [ ] Confirm "local: warm" badge goes green; run one Ask; run one Listen + speak + Space cycle with the external mic.
- [ ] Confirm `.env` has the cloud keys you want racing; watch which racer wins on the badge.
- [ ] If any speech script changed since 10 Sept, run content/08-cue-cards.regenerate.sh first so the cards match the teleprompter.
- [ ] Print content/08-cue-cards.pdf: 35 A5 cards, two per A4 sheet (landscape). Card 1 explains the deck. Card 1 lists where everything is; the six fallback rebuttals are the REBUT cards, tick the angle on the first LISTEN card and read the matching one if the screen dies. This replaces printing the separate scripts.
- [ ] Charge laptop. Pack: external mic (+ cable), power adapter, HDMI/USB-C adapter, phone with hotspot enabled.
- [ ] Read 01-opening-bit.md out loud 5 times. Time it: under 90 seconds.

## 15 minutes before
- [ ] Quit Teams, Zoom, Slack huddles, anything that owns the mic. Close heavy Chrome tabs (local model wants ~20 GB).
- [ ] System Settings > Sound > Input: select the external mic. Speak; watch the level meter move.
- [ ] Do Not Disturb on. Display sleep off (Settings > Lock Screen > never while on power). Lid stays open.
- [ ] Wi-Fi: venue Wi-Fi or phone hotspot. Test one Ask; note which racer wins. If all cloud racers error, that's fine:
      local still lands, just slower.
- [ ] `./run.sh`. Badge green. Font readable from where you'll stand. Zoom the browser (Cmd +) until it is.
- [ ] Press **Listen** as the MC starts. Leave it on. Check the transcript pane fills with the MC's words.

## What the guardrail does (so the screen does not surprise you)
- After a passage finishes, the app checks it for tic words, percentages that are not in the facts bank, and wording repeated from earlier tonight. If it finds one, the pane shows "rewriting..." and a new passage streams in a few seconds later. Wait for it; do not read the first draft.
- If three drafts all fail, it keeps the last one, scrubs the tic words, and logs a CHECK line (bottom right). Read that passage with a little more care.
- The percentage check cannot catch a real number attached to the wrong claim. That is still your job: if a number does not sound like one of the six facts you know, skip the sentence.

## Their numbers strip (under Running Notes)
- Every percentage they say appears as a chip: green with the source if it is in our facts bank, orange with "ask: which report, which year?" if not.
- Orange does not mean false. It means you ask for the source, out loud, and move on. If it was a made-up number, the silence does the work.
- If they read from a screen or mention their AI, Amit will call it out on its own. Your line is in the first speech: remember which side of the motion that supports.

## Reading the rebuttal pane
- The pane shows a ~70-second spoken passage in your voice, in short paragraphs. Read it as written or skim and riff. The last paragraph (orange) is the zinger you sit down on.
- Say "Amit 2.0 says" before you start reading. The attribution is the argument.
- Numbers: only the six facts in 07-facts-bank.md are allowed. If you see a number you don't recognise, skip that sentence.
- Anecdotes are written as shared scenes ("we've all watched a demo die at 8:59"). If one reads as a specific claim about you or Datasite that isn't true, reframe it live as "imagine..." or skip it.
- Tab toggles read mode (rebuttal fills the screen). It turns on automatically at STOP and off at Listen.

## Show mode (retired; the one-screen flow above in 00-run-of-show.md is the plan)
- Press S. Slot 1 is your scripted first speech. Arrow right when you sit; the mic starts for their speaker.
- Space the instant they say thank you. Arrow right; your script appears with Amit's passage inline where it belongs.
- Repeat for slot 4. In slot 4 Space produces the summary version (both speeches, concessions counted). Arrow right to slot 5.
- The timer under the rail goes orange in the last minute and red when over. Scripts are re-read from content/ every time you enter a slot, so edits on the day are fine.

## During
- Space = STOP & WRITE SPEECH 2 (whole 5-minute speech, written live). Press it the instant they say "thank you". Stand when the first page is full. Say "everything I'm about to say was written by Amit 2.0 in the seconds since Speaker A sat down", then read, turning pages with the arrow keys.
- After their second speaker: STOP & WRITE SUMMARY, not Space.
- L = Listen again. P = Panic lines. Enter in the Ask box for the opening bit.
- Never type during their speech. Glance at Running Notes only.
- If the transcript is garbage (wrong mic), press Clear, fix the input device, press Listen. Say nothing about it.

## Failure lines (also in the cheat sheet)
- Stall: "Still needs a human to hit retry. Give it five years. Or five seconds."
- Nonsense: "Even its hallucinations are faster than Amit's."
- Dead: "That is what a presales engineer looks like without Wi-Fi." Read from paper.

## Measured on this laptop (8 Sept 2026, 613-word mock opposition transcript)
| Path | First word | Full rebuttal |
|---|---|---|
| Local qwen3.6:35b-mlx, cold cache | 1.3 s | 2.6 s |
| Local qwen3.6:35b-mlx, warm cache, transcript grew by one sentence (the live case) | 0.65 s | 1.75 s |
| Local qwen3.6:35b GGUF, cold cache | 1.4 s | 2.5 s |
| Local qwen3.6:35b GGUF, warm cache, transcript grew by one sentence | 1.5 s | 3.1 s |
| Model load from cold (why run.sh warms it 15 min early) | 18-24 s | - |
| Apple STT, 5 s audio file | 0.4 s | - |
| Cerebras gpt-oss-120b (full transcript) | 0.4-1.1 s | 0.4-1.3 s |
| Groq gpt-oss-120b (full transcript) | 0.6-0.7 s | 0.9-1.0 s |
| Gemini 3.8 Flash | 4.3 s, no streaming, 503s | disabled |
| Apple STT live: each sentence lands 1-4 s after it is spoken; last words | 0.9 s after speech ends | - |
### Rehearsal run, 8 Sept 2026 (116 s of the mock speech through the laptop speakers into the built-in mic)
- 44 phrases captured; names still get mangled ("Buyers" once became "Myers"). The system prompt tells the model to expect this.
- Running notes refreshed at 27 s, 53 s, 76 s, 101 s. First two took ~3 s to first word; later ones 0.6-1.0 s once the cache was primed.
- Final rebuttal after STOP: first word 77 ms, complete in 1.2 s. The notes loop is what makes this near-instant.
- Local MLX runtime prefill: ~3 s when a request does not share its prefix with the previous one, ~0.5-0.8 s when it does.
  Live speeches are the good case (notes keep the cache aligned). The startup warm-up ends with an Ask so the opening bit is fast.
  Cloud racers (~1 s regardless) remove this concern; get the keys in.
- Stop-to-generate gap was 2.3 s waiting for the speech engine to finalise; now capped at 1.2 s.

Bake-off 8 Sept (Andrew scored blind): Groq 4/3, local 4/3, Cerebras 3/3, Gemini out. Cerebras and Groq run the same model, so that gap is noise. Racers: Cerebras, Groq, local.

Adversarial suite 01 (real opposition playbook), 9 Sept: with the cache primed by running notes, local won the rebuttal at 0.3 s to first word; the summary (longer context) took 2.5 s; cloud took over once at the 2.5 s deadline. Full passages 4-7 s, well ahead of reading speed.

Decision: MLX build is primary and the preferred racer. Keep the GGUF as fallback (or `ollama rm qwen3.6:35b` to free 23 GB).
