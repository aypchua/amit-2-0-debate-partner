# Verified facts bank
`app/prompts/facts.md` is the compact copy the model sees; it may cite ONLY these numbers. Anything else with a number is a
hallucination: cut it live. Verification column: **U** = Andrew opened the source, **M** = Claude opened the source or press
coverage of it, **A** = research agent found it via a mirror (Gartner.com blocks bots). Spot-check the **A** rows you plan to say out loud.

## For us (Proposition)
| Fact | Source | Ver |
|---|---|---|
| 67% of B2B buyers prefer a rep-free buying experience; 45% used AI tools in a recent purchase (646 buyers, Aug-Sep 2025) | Gartner press release, 9 Mar 2026. https://www.gartner.com/en/newsroom/press-releases/2026-03-09-gartner-sales-survey-finds-67-percent-of-b2b-buyers-prefer-a-rep-free-experience ; coverage https://www.digitalcommerce360.com/2026/03/17/gartner-b2b-buyers-rep-free-purchasing-ai-reshapes-sales/ | M |
| 70% prefer a completely digital self-service buying experience; 51% more likely to get misleading info from GenAI vs 49% from a sales rep; 7 info sources on average; 45% used GenAI (645 buyers) | Gartner press release, 20 May 2026. https://www.gartner.com/en/newsroom/press-releases/2026-05-20-gartner-survey-finds-sixty-nine-percent-of-b-two-b-buyers-turn-to-sales-reps-to-validate-ai-generated-insights | U |
| Gartner's own framing: sellers shift "from acting as the primary source of information to becoming a source of validation" (Robert Blaisdell, VP Analyst) | same release | U |
| By 2028 AI agents will outnumber human sellers 10:1 | Gartner press release, 18 Nov 2025. https://www.gartner.com/en/newsroom/press-releases/2025-11-18-gartner-predicts-by-2028-ai-agents-will-outnumber-sellers-by-10x-yet-fewer-than-40-percent-of-sellers-will-report-ai-agents-improved-productivity | A |
| 39% of B2B buyers willing to spend $500k+ per order via self-serve/remote (up from 28%); 20% at $1M+; in-person fell to 17% of revenue from 22% | McKinsey B2B Pulse, Sep 2024. https://www.digitalcommerce360.com/2024/09/12/more-b2b-buyers-are-willing-to-spend-big-bucks-per-online-order/ | A |
| 94% of B2B buyers used GenAI/conversational search; at the commit stage 30% saw GenAI as a meaningful interaction vs 17% for product experts | Forrester, "The State of Business Buying, 2026", Jan 2026. https://www.biia.com/forrester-b2b-buying-groups-expand-as-they-question-ai/ | A |
| 79% of RFP teams used GenAI in 2025 (68% in 2024); 62% use AI to generate answers (n=1,533) | Loopio, 2026 RFP Trends & Benchmarks, Mar 2026. https://loopio.com/blog/rfp-statistics-win-rates/ | A |
| 94% of SEs run repetitive demos; 34% say the standard demo has little/no customisation; 7 demos/week; automated demos close 19 days faster (with Presales Collective) | Navattic, State of Demo Automation 2026. https://www.navattic.com/report/state-of-demo-automation-2026 | A |
| 14% of B2B SaaS companies cut Sales Engineer headcount; 36% cut SDR/BDR (n=560+) | Emergence Capital / Benchmarkit, Beyond Benchmarks 2025. https://www.saastr.com/the-great-sdr-downsizing-36-of-b2b-companies-cut-sales-development-teams-in-2025/ | A |
| 22-25 year olds in AI-exposed jobs 19% below employment trend, via reduced hiring | Stanford Digital Economy Lab / ADP, "Canaries in the Coal Mine", Aug 2026 update. https://digitaleconomy.stanford.edu/news/canariesaug26/ | A |
| LLM inference cost falls ~10x/year; GPT-3-level from $60 to $0.06 per M tokens | a16z, "Welcome to LLMflation", Nov 2024. https://a16z.com/llmflation-llm-inference-cost/ | A |

## Theirs (pre-empt)
| Fact | Source | Ver | The flip |
|---|---|---|---|
| 69% of B2B buyers prefer to validate AI-generated insights with a sales rep | Gartner, 20 May 2026 (above) | U | Same buyers: 67% want no rep, 70% want fully digital. Our surviving job, in Gartner's words, is validation. Fact-checker for the robot is a countdown, not a career. |
| By 2030, 75% of B2B buyers will prefer sales experiences that prioritise human interaction over AI | Gartner, 25 Aug 2025. https://www.gartner.com/en/newsroom/press-releases/2025-08-25-gartner-says-by-2030-that-75-percent-of-b2b-buyers-will-prefer-sales-experiences-that-prioritize-human-interaction-over-ai | A | "Prefer a human somewhere" is not "need an SE in the room". A human account manager with an AI doing the demo is the motion, carried. |
| Rep-free buyers reported 23% higher purchase regret | Gartner, May 2021. https://www.gartner.com/en/newsroom/press-releases/gartner-says-b2b-sales-organizations-need-to-give-customers-a-se | A | 2021, pre-GenAI. Today buyers say reps mislead them almost as often as GenAI does (49% vs 51%). |
| 20% of buyers felt less confident after GenAI gave inaccurate info | Forrester, Jan 2026 (above) | A | And 49% expect misleading info from reps. Both sides hallucinate; only one costs a salary. |
| Over 40% of agentic AI projects will be cancelled by end 2027 (cost, unclear value, weak risk controls); only ~130 of thousands of agentic vendors are real | Gartner, 25 Jun 2025. https://www.gartner.com/en/newsroom/press-releases/2025-06-25-gartner-predicts-over-40-percent-of-agentic-ai-projects-will-be-canceled-by-end-of-2027 | M | 60% ship. Adoption lag is the buyer's problem; replacing us is the vendor's payroll decision. |
| AI and information processing create 11M jobs, displace 9M by 2030 (170M / 92M across all drivers) | WEF, Future of Jobs Report 2025, Jan 2025. https://www.weforum.org/publications/the-future-of-jobs-report-2025/digest/ | M | The 9M displaced are specific professions. Net positive is no comfort to the one being netted out. |
| The Brynjolfsson study (5,179 agents, +14%, +34% novices) | NBER w31161 / QJE 2025. https://www.nber.org/papers/w31161 | M | Novices gain, experts don't: the expertise premium collapses. Their evidence is ours. |
| ILO/NASK 2025: 1 in 4 workers exposed; transformation likelier than elimination | https://www.ilo.org/sites/default/files/2025-05/Research%20brief_GenAI%202025%20Update.pdf | M | Transformation is what replacement is called while it is happening to you. |
| McKinsey B2B Pulse: buyers use ~10 interaction channels; humans handle the complex ones | https://www.mckinsey.com/capabilities/growth-marketing-and-sales/our-insights/five-fundamental-truths-how-b2b-winners-keep-growing | A (their citation) | Ten channels, and most have no human in them. The human channel is the one shrinking. |

Dropped for lack of a primary source: AI note-taker adoption stat; "SE postings -14% / FDE +380%" vendor claim.
