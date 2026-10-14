const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, PageOrientation, AlignmentType, PageNumber, Header, Footer, BorderStyle } = require("docx");

// ---------- content ----------
// Each card: {tag, title, time, lines:[...], big?:bool, note?:string}. Lines are spoken text unless prefixed with "> " (stage direction) or "- " (bullet-ish, rendered as a short line).
const cards = [];
const add = (tag, title, time, lines, opts = {}) => cards.push({ tag, title, time, lines, ...opts });

add("HOW TO USE", "Backup deck", "", [
  "> Laptop dies, Wi-Fi dies, or you just want paper. This deck covers the whole night.",
  "> Cards 2-9: your first speech, scripted. Read them.",
  "> Card 10: listen card for their first speaker. Tick the angle they take.",
  "> Cards 11-20: second speech. Bridge (11), hand-over (12), ONE rebuttal card matching their angle (13-18), your points (19) and close (20).",
  "> Card 21: listen card for their second speaker.",
  "> Cards 22-30: summary. Frame (22), concessions (23), hand-over (24), ONE closing card per angle (25-29), final close (30).",
  "> Cards 31-35: their lines and yours (31-33), the six facts (34), failure lines (35).",
  "> Print two per sheet on A4 landscape. Number order is speaking order.",
]);

// ---- Slot 1: First Proposition (scripted) ----
add("1ST PROP", "Opening", "0:00", ["> Stand. Look at the empty chair.", "\"Before I get to the motion, some housekeeping. My teammate Amit sends his apologies. He couldn't make it tonight, which for a debate about whether AI replaces us is either very bad timing or very good timing.\"", "\"So on the way here, I replaced him.\"", "> Turn the screen towards the room.", "\"This is Amit 2.0. It runs on this laptop, it took me one afternoon, and it costs a fraction of a cent every time it opens its mouth. It's listening right now. When Speaker A and Speaker B sit down, it will write my second speech from what they actually said, and I will read it to you word for word, unchecked. Which is more trust than I ever gave Amit.\"", "\"And one small request while we're here. If at any point tonight the opposition consults a screen, just quietly note which side of the motion that supports.\""]);
add("1ST PROP", "What \"replace\" means", "1:00", ["\"The motion says AI will replace us in five years. Let me pin down 'replace', because the opposition is going to spend ten minutes living inside that word.\"", "\"Replaced means the buyer reaches a decision without needing a human presales engineer in the room.\"", "\"It doesn't mean zero headcount. Somewhere in this city there is still a man who fixes typewriters, and good for him. But when Speaker A tells you there'll still be a human in the loop, hear what it means for the ten of us who used to run the demos: two stay behind to watch the machine run them. That isn't a profession surviving. That's a profession with two witnesses.\""]);
add("1ST PROP", "What we actually do all day", "1:45", ["\"Let's be honest about the job. We're among friends and nobody from procurement is here.\"", "- Discovery calls. The AI note-taker in your last call listened better than you did, and had the follow-up drafted before you found your charger.", "- Demos. Generated per prospect now, and watched at one-and-a-half speed because nobody wants to sit through 'and if I just click here'.", "- RFPs and security questionnaires. Hands up if you still fill one in by hand. Nobody. That pillar fell two years ago and we threw a party.", "- POCs. An agent provisions the trial, loads the sample data and answers the tickets while we're asleep.", "- Objection handling. The documentation plus a model beats 'let me check with product' every time, because the model actually checked.", "\"Five pillars, and every one already has a product. What we do is stand between those products and glue them together with our calendars, and the glue is always the first thing automated.\""]);
add("1ST PROP", "What they'll say next", "2:45", ["\"Speaker A and Speaker B are about to tell you that fewer people per deal isn't the same as no people in the profession. Let me save them the trouble: they're right, and it doesn't help them. Singapore had bus conductors until the eighties, somebody on the 174 with a ticket punch. There are still bus conductors somewhere in the world, and not one person in this room is planning to become one. The motion says replace us. Us. The people in this room.\""]);
add("1ST PROP", "Five years is a long time", "3:15", ["\"They'll say five years is too soon. Look backwards five years instead. September 2021: GPT-3 was a party trick that could just about write a limerick. If I'd told you then that a laptop would rebut you live, in one second, in your own words, you'd have laughed. In ten minutes you get to watch it. Don't judge this motion by what the thing does today. Judge it by how far it came in five years, then go the same distance again.\""]);
add("1ST PROP", "Buyers never wanted us", "3:50", ["\"Here's the uncomfortable one. Buyers never wanted us. They wanted the answer, and for twenty years we were the slowest way to get it.\"", "\"Gartner asked 646 B2B buyers this year. Sixty-seven percent said they'd prefer a buying experience with no rep at all. Not fewer meetings. None. Think about the last deal you won and ask whether the buyer picked you because they liked the SE, or because the SE answered the question. Answers are free now. So what exactly is left to sell?\""]);
add("1ST PROP", "Close", "4:30", ["\"And it won't even be the buyer who makes the call. It'll be our own CFO, with a spreadsheet comparing cost per demo, and that spreadsheet already exists. Somebody in finance built it with AI while we were on a discovery call being empathetic.\"", "\"I came here one person short. Everything the opposition is about to say, my laptop has already predicted. Let's see how close it gets.\"", "> Sit."]);

// ---- Slot 2: listen ----
add("LISTEN", "Their first speaker", "5:00", [
  "> Do not stand. Tick the angle. Note their numbers and exact phrases.",
  "- ☐ Accountability gap: 'AI can generate the answer, a human must stand behind it'",
  "- ☐ Productivity creates more presales: 'they assume a fixed pile of work'",
  "- ☐ Enterprise last mile: 'we are debating the enterprise, not the frontier model'",
  "- ☐ Buying is social: 'transactions can be automated, commitment is social'",
  "- ☐ Motion on trial: 'they proved can, may, some; the motion needs will, replace, us'",
  "- ☐ Mixed (their real playbook): pilot analogy, 14% study, demand, verification",
  "- Count: 'still' ___  'leaner' ___  'human in the loop' ___  'transformation' ___",
  "- Numbers they said: __________  (ask: which report, which year?)",
]);

// ---- Slot 3: Second Proposition ----
add("2ND PROP", "Bridge", "0:00", [
  "Thank you Speaker A. That was heartfelt. I want the room to notice something: the opposition spent five minutes telling you humans are irreplaceable, and every example was about the past. The meeting they had. The dinner they had. The call they took. Nostalgia is not a forecast.",
  "Also, I counted. They said 'still' ___ times and 'human in the loop' ___ times. 'Still' is the sound of a job shrinking. Concession noted.",
  "> If they said 'more productive, not redundant': 'More productive' means fewer of us per deal. That is replacement, said politely, by someone hoping to be a survivor.",
]);
add("2ND PROP", "Hand over to Amit", "1:00", [
  "Now. My teammate has been listening. Amit 2.0, what did you make of that?",
  "> If the screen is alive: read it, attributed. Then card 19.",
  "> If the screen is dead: 'Still needs a human to hit retry. Give it five years. Or five seconds.' Then pick ONE card from 13-18 matching the angle you ticked, and read it as Amit's answer.",
]);
add("REBUT A", "Accountability gap", "~1:15", [
  "You built your whole case on accountability, for a job that never held the pen. Standing behind an answer is a signature, and the signature belongs to Legal and the CRO. We were the footnote. Nobody has ever fired a vendor's SE for a wrong answer. You sue the vendor.",
  "Who joins the escalation call? Customer success, on a contract, with an SLA. The SE was already on the next demo.",
  "You say we move up to validation. Gartner's own word for that role is validation, and Gartner says buyers expect reps to mislead them almost as often as GenAI. Fact-checker for the robot is a countdown, not a promotion.",
  "Recital of the approved answer is the most automatable job in the building. And that was the job.",
]);
add("REBUT B", "Productivity creates more presales", "~1:15", [
  "Cheaper demos mean more demos, you said. Agreed. Who watches them? Gartner asked 646 buyers this year: 67% prefer no rep at all, 70% want a fully digital purchase. The pile grows and the humans do not.",
  "Cloud did not fire developers, you said. Correct. It fired the sysadmins who racked the servers. In that analogy we are the sysadmins.",
  "One SE supporting eight deals instead of four removes half of us and calls it growth. Concession noted.",
  "The BLS projects 3% growth for sales engineers over a decade, with openings that exist because people leave. That is an exit queue, not a hiring boom. And nobody at the BLS forecast the end of the travel agent either.",
]);
add("REBUT C", "Enterprise last mile", "~1:15", [
  "'It worked in the demo.' That was our sentence, and the demo is now the product: the buyer runs it in their own tenant. The last mile used to be us. It is now a signup form.",
  "Twenty steps at 99% gives 82%, you said. Run that arithmetic on a twenty-step human deal cycle, where nobody is 99% reliable per step. Ask anyone who has sent the wrong pricing sheet.",
  "Enterprises adopt at the speed of governance, you said. We are not debating the enterprise's adoption of AI. We are debating our employer's adoption of AI to sell to the enterprise, and vendors adopt sales automation at the speed of a quota.",
  "McKinsey's two-thirds haven't scaled yet. Yet. Five years is the yet.",
]);
add("REBUT D", "Buying is social", "~1:15", [
  "Commitment is social, you said. Commitment is a signature and a budget line. The social part is the sponsor's job and the account executive's job. Neither of them is presales.",
  "Coalition-building is the AE's job title. We were the technical answer in the room, and the answer is free now.",
  "A buyer's agent negotiating with a vendor's agent: count the humans in that sentence.",
  "Buyers want to know when they are talking to an AI, you said. Want to know, not want to avoid. And a third of Gen Z will let an agent shop for them. Gen Z is the buying committee in five years.",
  "Rarer human moments, you said. Rarer is the word. A rare moment is not a headcount.",
]);
add("REBUT E", "Motion on trial", "~1:15", [
  "Will, replace, us. Let me take them in order.",
  "Will: Gartner's 67% is present tense. Buyers already prefer no rep. I am not predicting, I am reporting.",
  "Replace: the buyer decides without needing us in the room. I said it first, and every 'still' and 'leaner' you said tonight confirms it.",
  "Us: this room. Ask who here still fills in a security questionnaire by hand.",
  "How many must disappear, you ask. Ask the switchboard operators what the threshold was. Nobody announced it. One day the job listing stopped appearing.",
  "A job is a bundle of tasks, you said. A bundle with a salary attached. Unbundle the tasks and the salary goes, whatever you call what is left.",
]);
add("REBUT F", "Their real playbook (mixed)", "~1:15", [
  "The pilot analogy is yours, and it cuts the other way. Autopilot took the flight engineer and the navigator out of the cockpit. We are the navigator. Nobody misses them mid-flight.",
  "The 14% study buried its own headline: novices gained 34%, experts almost nothing. That is the junior with AI matching the senior. The expertise premium is what presales gets paid for, and it just collapsed.",
  "AI cannot own a wrong answer, you said. Own it with what, a payslip? Legal owns the indemnity. We recited the approved answer.",
  "Transformation, not redundancy, says the ILO. Ask the travel agent what transformation felt like from the inside. It felt exactly like your speech.",
]);
add("2ND PROP", "Points 5 and 6", "3:00", [
  "Two seconds, one laptop, zero calendar invites. That is the second speaker the motion deserved. Two more points.",
  "'Human in the loop' is what the loop says right before it closes. Every automation wave started with a supervisor watching the machine. Ask the supervisors where they are now.",
  "Trust. Buyers give five stars to a stranger's car after eight minutes. They trust Google Maps over the taxi uncle who has driven the route for thirty years. Trust is built by being right, fast, every time. Which of us in this room is right, fast, every time?",
]);
add("2ND PROP", "Point 7 and close", "4:15", [
  "Here's the thing we don't say out loud. Presales is the one job whose main deliverable is proving the buyer can't do it without us. We have spent our careers demoing our own indispensability. Tonight I demoed the opposite, one person short.",
  "The opposition will now stand up and tell you, one more time, that the human touch is irreplaceable. I have asked my teammate to write their speech in advance. Let's see how close it gets.",
  "> Sit.",
]);

// ---- Slot 4: listen ----
add("LISTEN", "Their second speaker", "5:00", [
  "> Same drill. New angle or same angle? Tick it. Note fresh points and numbers.",
  "- ☐ Accountability   ☐ Productivity   ☐ Last mile   ☐ Social   ☐ Motion on trial   ☐ Mixed",
  "- Their newest point: ______________________________",
  "- Count: 'still' ___  'leaner' ___  'human in the loop' ___  'transformation' ___",
  "- Numbers they said: __________  (ask: which report, which year?)",
  "- Did they consult a screen or mention their AI?  ☐ yes  →  use card 35, line 1",
]);

// ---- Slot 5: Summary ----
add("SUMMARY", "Frame what happened", "0:00", [
  "Let's take stock. Two speakers, ten minutes, and the opposition's case came down to three words: trust, complexity, and 'still'. Trust that buyers no longer give to humans first. Complexity that exists because humans are in the process. And 'still', which is the sound of a job getting smaller while it insists it is fine.",
]);
add("SUMMARY", "Count the concessions", "0:30", [
  "Here is what the opposition conceded tonight, in their own words:",
  "- 'Teams may become leaner.' Leaner is fewer of us.",
  "- 'More productive.' More productive is fewer of us per deal.",
  "- 'A human in the loop.' A supervisor of ten automated demos is not a presales engineer.",
  "- 'Transformation, not replacement.' Every replaced profession was transformed first.",
  "They argued the date. They never argued the direction. The motion only needs the direction.",
]);
add("SUMMARY", "Amit's last word", "1:15", [
  "My teammate listened to their closing. Amit 2.0?",
  "> Screen alive: read two or three sentences. Screen dead: read ONE closing card, 25-29, matching their angle.",
  "Notice it did that in the time it took them to sit down.",
]);
add("CLOSE A", "Accountability", "~0:40", [
  "Their last stand was accountability. Someone must stand behind the answer. Someone does: Legal, the CRO, customer success on an SLA. Not one of those is a presales engineer, and not one of them was tonight. The buyer trusts the sandbox in their own tenant over a person saying 'trust me'. When the answer proves itself, the person who used to vouch for it is not transformed. They are excused.",
]);
add("CLOSE B", "Productivity", "~0:40", [
  "Their last stand was economics: cheaper work means more work. Where does the extra work go? To the channel with no human in it. Gartner: 67% prefer no rep, 70% want a fully digital purchase. Their own example, one SE on eight deals, removes half of us and calls it growth. Productivity is not proof of extinction, they said. It is the mechanism of it.",
]);
add("CLOSE C", "Last mile", "~0:40", [
  "Their last stand was the last mile: enterprises move slowly. The buyer's adoption is not the question. Our employer's is, and it moves at the speed of a quarterly cost review. Two-thirds haven't scaled yet, they said. Yet. Five years is the yet. And the last mile is a signup form now.",
]);
add("CLOSE D", "Social", "~0:40", [
  "Their last stand was that commitment is social. Commitment is a signature and a budget line. The social part belongs to the sponsor and the account executive, and always did. We were the answer in the room, and the answer is free. A buyer's agent and a vendor's agent negotiating: count the humans. Zero. That is the room in five years.",
]);
add("CLOSE E", "Motion on trial", "~0:40", [
  "Their last stand was the dictionary: will, replace, us. Will: present tense, Gartner's buyers already prefer no rep. Replace: the buyer decides without us in the room, and every 'leaner' they said tonight agreed. Us: this room, and nobody here still fills in a questionnaire by hand. They proved transformation. Transformation is what replacement is called while it is happening to you.",
]);
add("SUMMARY", "Definition and final close", "2:00", [
  "Replaced means the buyer reaches a decision without needing one of us in the room. Not zero headcount. Not tomorrow. Within five years. Five years ago the thing on this table was a party trick. Tonight it out-argued two professionals on their own turf, and the only human it needed was one to hit the space bar.",
  "I came here one person short. I leave with the motion carried, and my teammate never once said 'let me get back to you'. The opposition argued, passionately, that they are irreplaceable. They did it in the exact words my laptop predicted. Thank you.",
  "> Sit on the laugh. Add nothing.",
]);

// ---- Reference cards ----
add("THEIR LINE → YOURS", "Cheat sheet 1", "", [
  "- 'AI hallucinates.' → So do SEs. We call it 'roadmap'.",
  "- 'Complex deals need humans.' → Complexity is a symptom of humans.",
  "- 'AI can't read the room.' → The room is a Zoom call with cameras off.",
  "- 'Regulated industries.' → The security questionnaire was the first thing automated.",
  "- 'Trust is built over years.' → Buyers trust Google Maps over a local.",
  "- 'Relationships close deals.' → Procurement portals close deals.",
  "- 'You're arguing yourself out of a job.' → I'm the one hitting retry. For now.",
]);
add("THEIR LINE → YOURS", "Cheat sheet 2", "", [
  "- 'Calculators are accurate, humans still own the decision.' → And the profession called 'computer' is gone. The CFO stayed. We are not the CFO in that analogy. We are the room.",
  "- 'Gartner: 40% of agentic projects cancelled.' → So Gartner expects 60% to ship. And it is our employer's adoption that matters, decided at a cost review.",
  "- 'Access to information is not confidence.' → Confidence comes from watching it work in your own tenant. It never came from 'trust me'.",
  "- 'A person using AI is still a person.' → Yes: the account executive, or the buyer. The person who leaves answered the questions the AI now answers.",
  "- 'Thank-you card for PowerPoint archaeology.' → Amit will file it under exit interview.",
]);
add("THEIR LINE → YOURS", "Cheat sheet 3", "", [
  "- 'You automated the artefact, not the accountability.' → Accountability is a signature. Ask Legal whose name is on the indemnity.",
  "- 'Cheapest answer, most expensive mistake.' → So can the slowest. Ask anyone who lost a deal to 'let me circle back'.",
  "- 'Self-service removes friction, not uncertainty.' → Evidence removes uncertainty. The sandbox is evidence. The human is the friction.",
  "- 'Restructuring proves change, not replacement.' → Ask the typists when the reduction became replacement. They were not consulted.",
  "- NEVER SAY: 'people who use AI will replace people who don't'. It is their trap.",
]);
add("FACTS", "The six you may say aloud", "", [
  "- Gartner, March 2026, 646 buyers: 67% prefer a rep-free experience; 45% used AI in a recent purchase.",
  "- Gartner, May 2026, 645 buyers: 70% prefer a fully digital self-service purchase. 51% expect misleading info from GenAI, 49% from a sales rep: almost as often. 69% like to validate AI insights with a rep. Their word: validation.",
  "- NBER / QJE, 5,179 support agents: +14% productivity, +34% for novices, experts almost nothing.",
  "- Emergence Capital, 2025: 14% of B2B SaaS companies cut sales-engineer headcount.",
  "- Navattic with Presales Collective, 2026: 94% of SEs run repetitive demos; automated demos close 19 days faster.",
  "- Gartner, Nov 2025: by 2028 AI agents outnumber human sellers ten to one.",
  "> Any other number: skip it, or ask them 'which report, which year?'",
]);
add("IF IT BREAKS", "Failure lines", "", [
  "- They consult a screen / mention their AI → 'Two skilled presales professionals needed a machine to explain why the machine can't replace them. That is not a rebuttal, that is a demonstration.'",
  "- Screen stalls → 'Still needs a human to hit retry. Give it five years. Or five seconds.'",
  "- Screen prints nonsense → 'Even its hallucinations are faster than Amit's.'",
  "- Screen dead → 'That is what a presales engineer looks like without Wi-Fi.' Then read the matching REBUT card.",
  "- They give you nothing to work with → 'Exactly. Even the opposition doesn't want to feed it.'",
  "- You lose your place → Say the definition. 'Replaced means the buyer decides without needing us in the room.' Then find the card.",
]);


// ---------- computed cross-references (card numbers change when the script changes) ----------
{
  const idx = (pred) => cards.map((c, i) => (pred(c) ? i + 1 : null)).filter(Boolean);
  const rng = (a) => (a.length ? (a.length === 1 ? `${a[0]}` : `${a[0]}-${a[a.length - 1]}`) : "?");
  const prop1 = idx(c => c.tag === "1ST PROP"), listen = idx(c => c.tag === "LISTEN"), prop2 = idx(c => c.tag === "2ND PROP");
  const rebut = idx(c => c.tag.startsWith("REBUT")), close = idx(c => c.tag.startsWith("CLOSE")), summ = idx(c => c.tag === "SUMMARY");
  const cheat = idx(c => c.tag === "THEIR LINE → YOURS"), facts = idx(c => c.tag === "FACTS"), fail = idx(c => c.tag === "IF IT BREAKS");
  const handover = prop2[1], pointsCard = prop2[2], bridge = prop2[0], closeCard = prop2[3];
  cards[0].lines = [
    "> Laptop dies, Wi-Fi dies, or you just want paper. This deck covers the whole night.",
    `> Cards ${rng(prop1)}: your first speech, scripted. Read them.`,
    `> Card ${listen[0]}: listen card for their first speaker. Tick the angle they take.`,
    `> Cards ${bridge}-${closeCard}: second speech. Bridge (${bridge}), hand-over (${handover}), ONE rebuttal card matching their angle (${rng(rebut)}), your points (${pointsCard}) and close (${closeCard}).`,
    `> Card ${listen[1]}: listen card for their second speaker.`,
    `> Cards ${summ[0]}-${summ[summ.length - 1]}: summary. Frame (${summ[0]}), concessions (${summ[1]}), hand-over (${summ[2]}), ONE closing card per angle (${rng(close)}), final close (${summ[3]}).`,
    `> Cards ${cheat[0]}-${fail[0]}: their lines and yours (${rng(cheat)}), the six facts (${facts[0]}), failure lines (${fail[0]}).`,
    "> Print two per sheet on A4 landscape. Number order is speaking order.",
  ];
  const fix = (s) => s.replace(/Then card \d+\./, `Then card ${pointsCard}.`).replace(/ONE card from \d+-\d+/, `ONE card from ${rng(rebut)}`)
    .replace(/use card \d+, line 1/, `use card ${fail[0]}, line 1`).replace(/ONE closing card, \d+-\d+,/, `ONE closing card, ${rng(close)},`);
  for (const c of cards) c.lines = c.lines.map(fix);
}

// ---------- rendering ----------
const A5W = 8391, A5H = 11907; // portrait DXA; landscape via orientation
const font = "Helvetica Neue";
const mkRun = (text, o = {}) => new TextRun({ text, font, ...o });
const para = (line) => {
  if (line.startsWith("> ")) return new Paragraph({ spacing: { after: 140 }, children: [mkRun(line.slice(2), { italics: true, size: 24, color: "666666" })] });
  if (line.startsWith("- ")) return new Paragraph({ spacing: { after: 110 }, indent: { left: 240, hanging: 240 }, children: [mkRun("–  " + line.slice(2), { size: 26 })] });
  return new Paragraph({ spacing: { after: 200 }, children: [mkRun(line, { size: 30 })] });
};
const sections = cards.map((c, i) => ({
  properties: { page: { size: { width: A5W, height: A5H, orientation: PageOrientation.LANDSCAPE }, margin: { top: 500, bottom: 500, left: 640, right: 640 } } },
  headers: { default: new Header({ children: [new Paragraph({
    border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: "999999", space: 4 } },
    children: [mkRun(`${c.tag}   `, { bold: true, size: 20, color: "B36B00" }), mkRun(c.title, { bold: true, size: 26 }), mkRun(c.time ? `      ${c.time}` : "", { size: 20, color: "666666" })],
  })] }) },
  footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [mkRun(`card ${i + 1} of ${cards.length}`, { size: 18, color: "999999" })] })] }) },
  children: [new Paragraph({ spacing: { after: 60 }, children: [] }), ...c.lines.map(para)],
}));
const doc = new Document({ creator: "AMIT 2.0", title: "PSC debate cue cards", styles: { default: { document: { run: { font, size: 28 } } } }, sections });
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync("cue-cards.docx", buf); console.log("wrote cue-cards.docx with", cards.length, "cards"); });
