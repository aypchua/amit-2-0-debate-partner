#!/bin/zsh
# Rebuild the cue-card deck after editing 08-cue-cards.source.js (cards mirror the speech scripts; keep both in step).
# Produces 08-cue-cards.docx, 08-cue-cards.html and 08-cue-cards.pdf (PDF via Chrome headless).
set -e
cd "$(dirname "$0")"
export NODE_PATH="$PWD/.tools/node_modules"
node 08-cue-cards.source.js >/dev/null
mv -f cue-cards.docx 08-cue-cards.docx
node -e '
const fs=require("fs");
const src=fs.readFileSync("08-cue-cards.source.js","utf8").replace(/^Packer\.toBuffer[\s\S]*$/m,"fs.writeFileSync(\"cards.json\", JSON.stringify(cards));");
fs.writeFileSync(".tools/_cards_json.js", src);'
node .tools/_cards_json.js >/dev/null
python3 - <<'PY'
import json, html
cards=json.load(open('cards.json'))
css=open('08-cue-cards.html').read().split('<style>')[1].split('</style>')[0]
def r(l):
    if l.startswith("> "): return f'<p class="dir">{html.escape(l[2:])}</p>'
    if l.startswith("- "): return f'<p class="li">– {html.escape(l[2:])}</p>'
    return f'<p>{html.escape(l)}</p>'
n=len(cards); out=['<!doctype html><html><head><meta charset="utf-8"><title>PSC debate cue cards</title><style>'+css+'</style></head><body>']
for i,c in enumerate(cards,1):
    out.append(f'<section class="card"><div class="hd"><span class="tag">{html.escape(c["tag"])}</span><span class="title">{html.escape(c["title"])}</span><span class="time">{html.escape(c.get("time",""))}</span></div><div class="body">'+"".join(r(l) for l in c["lines"])+f'</div><div class="ft">card {i} of {n}</div></section>')
out.append('</body></html>'); open('08-cue-cards.html','w').write("\n".join(out)); print(n,'cards')
PY
rm -f cards.json
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --no-pdf-header-footer --print-to-pdf="$PWD/08-cue-cards.pdf" "file://$PWD/08-cue-cards.html" 2>/dev/null
python3 -c "import re; d=open('08-cue-cards.pdf','rb').read(); print('pdf pages:', len(re.findall(rb'/Type\s*/Page[^s]', d)))"
