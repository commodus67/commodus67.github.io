#!/usr/bin/env python3
"""Regenerate soccer-predictions-demo.html from the live Apify Actor.

Run by .github/workflows/refresh-predictions.yml. Needs APIFY_TOKEN in the
environment; the token never reaches the published page, only the numbers do.
"""
import datetime
import json
import os
import sys
import urllib.error
import urllib.request

ACTOR = "commodus67~soccer-dixon-coles-match-predictor"
INPUT = {"seasonsBack": 3, "xi": 0.0018, "upcomingDays": 14, "maxGoals": 10}
OUT = "soccer-predictions-demo.html"

LEAGUES = [
    ("eng.1", "Premier League", "EN"),
    ("esp.1", "LaLiga", "ES"),
    ("ita.1", "Serie A", "IT"),
    ("ger.1", "Bundesliga", "DE"),
    ("fra.1", "Ligue 1", "FR"),
    ("usa.1", "MLS", "US"),
    ("mex.1", "Liga MX", "MX"),
    ("mex.2", "Liga de Expansion MX", "MX"),
    ("bra.2", "Brasileirao Serie B", "BR"),
    ("usa.usl.1", "USL Championship", "US"),
    ("col.1", "Colombia Primera A", "CO"),
    ("uru.1", "Uruguay Primera Division", "UY"),
    ("nor.1", "Eliteserien", "NO"),
]

NAMES = {
    "mex.2": "Liga de Expansi\u00f3n MX",
    "bra.2": "Brasileir\u00e3o S\u00e9rie B",
    "uru.1": "Uruguay Primera Divisi\u00f3n",
}


HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-1XML9M4WYT"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());

var gaInternal = false;
try {
  if (/[?&]internal=1(&|$)/.test(location.search)) localStorage.setItem('ga_internal', '1');
  if (/[?&]internal=0(&|$)/.test(location.search)) localStorage.removeItem('ga_internal');
  gaInternal = localStorage.getItem('ga_internal') === '1';
} catch (e) {}
gtag('config', 'G-1XML9M4WYT', gaInternal ? { traffic_type: 'internal' } : {});
</script>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Soccer Match Predictions — 1X2, Over/Under &amp; BTTS Odds</title>
<meta name="description" content="Dixon-Coles match probabilities for the Premier League, LaLiga, Serie A, Bundesliga, Ligue 1, MLS, Liga MX, Brasileirao Serie B, USL Championship, Colombia, Uruguay and Eliteserien. 1X2, Over/Under, Both Teams To Score and exact scorelines. No API key needed.">
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:#070c1a;color:#e8eaf6;font-family:'Segoe UI',system-ui,-apple-system,sans-serif;min-height:100vh;-webkit-font-smoothing:antialiased}
  .wrap{max-width:640px;margin:0 auto;padding:20px 16px 48px}
  @keyframes fadeUp{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}
  ::-webkit-scrollbar{width:6px;height:6px}
  ::-webkit-scrollbar-track{background:#0c1428}
  ::-webkit-scrollbar-thumb{background:#2a3560;border-radius:3px}
  .card{background:#0c1428;border:1px solid #1a2440;border-radius:14px;padding:14px}
  .eyebrow{font-size:9px;letter-spacing:2px;color:#3a4570;font-weight:700;text-transform:uppercase}
  h1{font-size:27px;font-weight:900;letter-spacing:-1.2px;background:linear-gradient(135deg,#00e676,#00bcd4);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;color:#00e676;line-height:1.15}
  .chip{padding:6px 11px;border-radius:8px;border:none;cursor:pointer;font-size:11.5px;font-weight:700;background:#111d38;color:#5a6a99;transition:background .15s,color .15s;font-family:inherit}
  .chip[aria-pressed="true"]{background:#00e676;color:#070c1a}
  .cc{display:inline-block;font-style:normal;font-size:9px;font-weight:800;letter-spacing:.5px;
      padding:2px 4px;margin-right:6px;border-radius:4px;background:#1e2b4d;color:#8fa3d4;vertical-align:1px}
  .chip[aria-pressed="true"] .cc{background:#0a3b22;color:#00e676}
  .chip:focus-visible{outline:2px solid #00bcd4;outline-offset:2px}
  .lowd{display:inline-block;font-size:8.5px;font-weight:800;letter-spacing:.5px;
        padding:1px 4px;margin-left:6px;border-radius:3px;background:#3a2c0a;color:#ffd600;vertical-align:1px}
  .mrow{display:grid;grid-template-columns:58px 1fr auto;gap:10px;align-items:center;width:100%;text-align:left;
        background:transparent;border:none;border-bottom:1px solid #141d35;padding:9px 6px;cursor:pointer;color:inherit;font-family:inherit;font-size:13px}
  .mrow:last-child{border-bottom:none}
  .mrow:hover{background:#111d38}
  .mrow[aria-current="true"]{background:#11291f;box-shadow:inset 3px 0 0 #00e676}
  .mrow .d{font-size:10px;color:#3a4570;line-height:1.35;white-space:nowrap}
  .mrow .t{line-height:1.35}
  .mrow .t b{font-weight:600}
  .mini{display:flex;height:4px;border-radius:2px;overflow:hidden;width:56px;flex-shrink:0}
  table{width:100%;border-collapse:collapse}
  td{padding:7px 0;border-bottom:1px solid #141d35;font-size:12.5px}
  tr:last-child td{border-bottom:none}
  .num{font-variant-numeric:tabular-nums}
  a{color:#00bcd4}
  @media(max-width:430px){
    .wrap{padding:16px 12px 40px}
    h1{font-size:23px}
    .mrow{grid-template-columns:58px 1fr auto;gap:7px;font-size:12px}
  }
</style>
</head>
<body>
<div class="wrap">

  <header style="text-align:center;margin-bottom:18px">
    <div style="font-size:10px;letter-spacing:3px;color:#00e676;font-weight:700;margin-bottom:6px">DIXON&ndash;COLES &middot; BIVARIATE POISSON</div>
    <h1><span style="-webkit-text-fill-color:initial;color:initial">&#9917;</span> Soccer Match Predictions</h1>
    <p style="color:#3a4a70;margin-top:5px;font-size:12px">1X2 &middot; Over/Under &middot; Both Teams To Score &middot; Exact score</p>
    <p id="hdrStats" style="color:#2f3c63;margin-top:3px;font-size:11px"></p>
  </header>

  <section class="card" style="margin-bottom:12px">
    <div class="eyebrow" style="margin-bottom:9px">League</div>
    <div id="leagues" style="display:flex;gap:6px;flex-wrap:wrap"></div>
  </section>

  <section class="card" style="margin-bottom:12px;padding:10px 8px">
    <div class="eyebrow" style="margin:2px 0 8px 6px">Upcoming matches <span id="mCount" style="color:#2f3c63"></span></div>
    <div id="matches" style="max-height:290px;overflow-y:auto"></div>
  </section>

  <div id="detail"></div>

  <footer style="margin-top:18px;font-size:10.5px;color:#3a4570;line-height:1.7">
    <div class="card" style="padding:11px 14px">
      Probabilities come from a Dixon&ndash;Coles bivariate Poisson model fitted by maximum likelihood on finished matches from the public ESPN feed, with exponential time decay so recent results weigh more. The full scoreline grid is recomputed in your browser from the fitted goal rates, so every market on this page is internally consistent.
      <div style="margin-top:8px;color:#4a5580">Simulation and data, not tips. Nothing here is betting advice.</div>
      <div style="margin-top:8px">Powered by <a id="actorLink" href="#" target="_blank" rel="noopener">soccer-dixon-coles-match-predictor</a> on Apify &middot; <span id="gen"></span></div>
    </div>
  </footer>
</div>

<script id="payload" type="application/json">__DATA__</script>
<script>
(function(){
  "use strict";
  var DATA = JSON.parse(document.getElementById("payload").textContent);
  var MAXG = 10, LINES = [0.5,1.5,2.5,3.5,4.5];
  var state = { li:0, mi:0, line:2.5 };

  var fact=[1];for(var i=1;i<=MAXG+1;i++)fact[i]=fact[i-1]*i;
  function pois(k,l){return Math.exp(-l)*Math.pow(l,k)/fact[k];}

  function grid(lh,la,rho){
    var g=[],s=0,x,y,p,tau;
    for(x=0;x<=MAXG;x++){g[x]=[];for(y=0;y<=MAXG;y++){
      p=pois(x,lh)*pois(y,la);
      if(x===0&&y===0)tau=1-lh*la*rho;
      else if(x===0&&y===1)tau=1+lh*rho;
      else if(x===1&&y===0)tau=1+la*rho;
      else if(x===1&&y===1)tau=1-rho;
      else tau=1;
      g[x][y]=p*tau;s+=g[x][y];
    }}
    for(x=0;x<=MAXG;x++)for(y=0;y<=MAXG;y++)g[x][y]/=s;
    return g;
  }
  function markets(g,line){
    var p1=0,px=0,p2=0,ov=0,bt=0,x,y,v;
    for(x=0;x<=MAXG;x++)for(y=0;y<=MAXG;y++){
      v=g[x][y];
      if(x>y)p1+=v;else if(x===y)px+=v;else p2+=v;
      if(x+y>line)ov+=v;
      if(x>0&&y>0)bt+=v;
    }
    return {p1:p1,px:px,p2:p2,ov:ov,un:1-ov,bt:bt,nb:1-bt};
  }
  function topScores(g,n){
    var out=[],x,y;
    for(x=0;x<=MAXG;x++)for(y=0;y<=MAXG;y++)out.push({s:x+"–"+y,p:g[x][y]});
    out.sort(function(a,b){return b.p-a.p;});
    return out.slice(0,n);
  }
  function pct(v){return (v*100).toFixed(1);}
  function esc(s){return String(s).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}
  function when(iso){
    var d=new Date(iso);
    if(isNaN(d))return iso;
    return d.toLocaleDateString(undefined,{month:"short",day:"numeric"})+"<br>"+
           d.toLocaleTimeString(undefined,{hour:"numeric",minute:"2-digit"});
  }

  var elL=document.getElementById("leagues"),
      elM=document.getElementById("matches"),
      elD=document.getElementById("detail"),
      elC=document.getElementById("mCount");

  var totalM=0;DATA.leagues.forEach(function(l){totalM+=l.matches.length;});
  document.getElementById("hdrStats").textContent=
    totalM+" upcoming matches across "+DATA.leagues.length+" leagues";
  document.getElementById("actorLink").href=DATA.source.url;
  var gd=new Date(DATA.generatedAt);
  document.getElementById("gen").textContent="model run "+(isNaN(gd)?DATA.generatedAt:gd.toLocaleString());

  DATA.leagues.forEach(function(l,i){
    var b=document.createElement("button");
    b.className="chip";b.type="button";b.innerHTML='<i class="cc">'+esc(l.flag)+'</i>'+esc(l.name);
    b.setAttribute("aria-pressed",i===0?"true":"false");
    b.onclick=function(){state.li=i;state.mi=0;renderLeagues();renderMatches();renderDetail();
      elM.scrollTop=0;};
    elL.appendChild(b);
  });
  function renderLeagues(){
    [].forEach.call(elL.children,function(b,i){b.setAttribute("aria-pressed",i===state.li?"true":"false");});
  }

  function renderMatches(){
    var lg=DATA.leagues[state.li];
    elC.textContent="("+lg.matches.length+")";
    elM.innerHTML="";
    lg.matches.forEach(function(m,i){
      var mk=markets(grid(m.lh,m.la,lg.rho),2.5);
      var b=document.createElement("button");
      b.className="mrow";b.type="button";
      b.setAttribute("aria-current",i===state.mi?"true":"false");
      b.innerHTML='<span class="d">'+when(m.k)+'</span>'+
        '<span class="t"><b>'+esc(m.h)+'</b><br><span style="color:#7986cb">'+esc(m.a)+'</span>'+(m.q?'<span class="lowd">LOW DATA</span>':'')+'</span>'+
        '<span class="mini" title="1X2"><i style="flex:'+mk.p1+';background:#00e676"></i>'+
        '<i style="flex:'+mk.px+';background:#ffd600"></i>'+
        '<i style="flex:'+mk.p2+';background:#ff4081"></i></span>';
      b.onclick=function(){state.mi=i;renderMatches();renderDetail();};
      elM.appendChild(b);
    });
  }

  function bar(label,v,color){
    return '<div style="margin-bottom:13px">'+
      '<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:5px">'+
        '<span style="font-size:12.5px;color:#b0bec5">'+label+'</span>'+
        '<span class="num" style="font-size:21px;font-weight:900;color:'+color+';letter-spacing:-1px">'+pct(v)+'%</span>'+
      '</div>'+
      '<div style="background:#1a2340;border-radius:4px;height:8px;overflow:hidden">'+
        '<div style="width:'+(v*100)+'%;height:100%;background:'+color+';border-radius:4px"></div>'+
      '</div></div>';
  }
  function statCard(title,rows){
    var h='<div class="card"><div class="eyebrow" style="margin-bottom:11px">'+title+'</div>';
    rows.forEach(function(r,i){
      h+='<div style="margin-bottom:'+(i<rows.length-1?"10px":"0")+'">'+
         '<div style="font-size:10px;color:#3a4570">'+r.l+'</div>'+
         '<div class="num" style="font-size:23px;font-weight:900;color:'+r.c+';letter-spacing:-1px">'+r.v+'</div></div>';
    });
    return h+'</div>';
  }

  function renderDetail(){
    var lg=DATA.leagues[state.li], m=lg.matches[state.mi];
    if(!m){elD.innerHTML="";return;}
    var g=grid(m.lh,m.la,lg.rho), mk=markets(g,state.line), ts=topScores(g,5);
    var fav = mk.p1>mk.p2 ? {n:m.h,p:mk.p1,side:"home"} : (mk.p2>mk.p1 ? {n:m.a,p:mk.p2,side:"away"} : null);

    var h='<div style="animation:fadeUp .35s ease">';

    if(fav){
      h+='<div class="card" style="border-color:#00e676;background:linear-gradient(135deg,#040f09,#061409);text-align:center;margin-bottom:12px">'+
         '<div style="font-size:10px;letter-spacing:3px;color:#00e676;margin-bottom:5px">&#127942; MODEL FAVOURITE</div>'+
         '<div style="font-size:19px;font-weight:900;line-height:1.25">'+esc(fav.n)+'</div>'+
         '<div class="num" style="font-size:12px;color:#00a854;margin-top:4px">Win probability '+pct(fav.p)+'%</div></div>';
    }else{
      h+='<div class="card" style="border-color:#ffd600;text-align:center;margin-bottom:12px">'+
         '<div style="font-size:18px;font-weight:900;color:#ffd600">&#9878;&#65039; Too close to call</div></div>';
    }

    if(m.q){
      h+='<div class="card" style="border-color:#ffd600;background:#14120a;margin-bottom:12px;font-size:11.5px;color:#c9b458;line-height:1.55">'+
         '<b style="color:#ffd600">Low data.</b> One of these teams has fewer than 10 matches in the fitted history, typically a side newly promoted this season. '+
         'The model still returns a full set of probabilities, but the rating behind them rests on a small sample and will move a lot over the next few weeks.</div>';
    }

    h+='<div class="card" style="margin-bottom:12px">'+
       '<div class="eyebrow" style="margin-bottom:14px">Match result (1X2)</div>'+
       bar(esc(m.h)+" win", mk.p1, "#00e676")+
       bar("Draw", mk.px, "#ffd600")+
       bar(esc(m.a)+" win", mk.p2, "#ff4081")+'</div>';

    h+='<div class="card" style="margin-bottom:12px">'+
       '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:13px">'+
       '<span class="eyebrow">Total goals</span><span id="lineBtns" style="display:flex;gap:4px;flex-wrap:wrap"></span></div>'+
       bar("Over "+state.line, mk.ov, "#00bcd4")+
       bar("Under "+state.line, mk.un, "#7986cb")+'</div>';

    h+='<div class="card" style="margin-bottom:12px">'+
       '<div class="eyebrow" style="margin-bottom:14px">Both teams to score</div>'+
       bar("Yes", mk.bt, "#00e676")+
       bar("No", mk.nb, "#ff4081")+'</div>';

    h+='<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px">'+
       statCard("Expected goals",[
         {l:esc(m.h),v:m.lh.toFixed(2),c:"#00e676"},
         {l:esc(m.a),v:m.la.toFixed(2),c:"#ff4081"}])+
       statCard("Goals &amp; score",[
         {l:"Expected total",v:(m.lh+m.la).toFixed(2),c:"#00bcd4"},
         {l:"Most likely score",v:ts[0].s,c:"#7986cb"}])+
       '</div>';

    h+='<div class="card" style="margin-bottom:12px"><div class="eyebrow" style="margin-bottom:11px">Most likely scorelines</div>';
    ts.forEach(function(s){
      h+='<div style="display:grid;grid-template-columns:46px 1fr 52px;gap:9px;align-items:center;padding:5px 0">'+
         '<span class="num" style="font-size:14px;font-weight:800">'+s.s+'</span>'+
         '<span style="background:#1a2340;border-radius:3px;height:6px;overflow:hidden;display:block">'+
           '<span style="display:block;width:'+(s.p/ts[0].p*100)+'%;height:100%;background:#00bcd4"></span></span>'+
         '<span class="num" style="font-size:12px;color:#7986cb;text-align:right">'+pct(s.p)+'%</span></div>';
    });
    h+='</div>';

    h+='<div class="card"><div class="eyebrow" style="margin-bottom:9px">Model inputs</div><table>'+
       '<tr><td style="color:#3a4570">Low-score correlation &rho;</td><td class="num" style="text-align:right">'+lg.rho.toFixed(4)+'</td></tr>'+
       '<tr><td style="color:#3a4570">Finished matches fitted</td><td class="num" style="text-align:right">'+lg.historyMatches.toLocaleString()+'</td></tr>'+
       '<tr><td style="color:#3a4570">Seasons of history</td><td class="num" style="text-align:right">'+DATA.source.seasonsBack+'</td></tr>'+
       '<tr><td style="color:#3a4570">Goal grid</td><td class="num" style="text-align:right">'+MAXG+'&times;'+MAXG+'</td></tr>'+
       '</table></div>';

    h+='</div>';
    elD.innerHTML=h;

    var lb=document.getElementById("lineBtns");
    LINES.forEach(function(v){
      var b=document.createElement("button");
      b.className="chip";b.type="button";b.textContent=v.toFixed(1);
      b.style.padding="3px 8px";b.style.fontSize="10.5px";
      b.setAttribute("aria-pressed",v===state.line?"true":"false");
      b.onclick=function(){state.line=v;renderDetail();};
      lb.appendChild(b);
    });
  }

  renderMatches();renderDetail();
})();
</script>
</body>
</html>
"""


def fetch(slug, token):
    """Run the Actor for one league and return its dataset rows."""
    url = (
        "https://api.apify.com/v2/acts/" + ACTOR
        + "/run-sync-get-dataset-items?token=" + token
    )
    body = json.dumps(dict(INPUT, leagueSlug=slug)).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.load(resp)


def main():
    token = os.environ.get("APIFY_TOKEN", "").strip()
    if not token:
        sys.exit("APIFY_TOKEN is not set. Add it as a repository secret.")

    leagues, total = [], 0
    for slug, name, flag in LEAGUES:
        try:
            rows = fetch(slug, token)
        except urllib.error.HTTPError as exc:
            sys.exit("Actor call failed for %s: HTTP %s" % (slug, exc.code))
        if not rows:
            print("  %-12s no upcoming fixtures, skipped" % slug)
            continue
        matches = [
            {
                "k": r["kickoff"],
                "h": r["homeTeam"],
                "a": r["awayTeam"],
                "lh": round(r["lambdaHome"], 6),
                "la": round(r["lambdaAway"], 6),
                "q": 0 if r.get("dataQuality") == "full" else 1,
            }
            for r in rows
            if r.get("lambdaHome") is not None and r.get("lambdaAway") is not None
        ]
        matches.sort(key=lambda m: m["k"])
        leagues.append({
            "slug": slug,
            "name": NAMES.get(slug, name),
            "flag": flag,
            "rho": round(rows[0]["rho"], 6),
            "historyMatches": rows[0]["historyMatches"],
            "matches": matches,
        })
        total += len(matches)
        print("  %-12s %3d matches" % (slug, len(matches)))

    if total == 0:
        sys.exit("Every league came back empty; refusing to publish an empty page.")

    doc = {
        "generatedAt": datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "model": "Dixon-Coles bivariate Poisson, MLE-fitted attack/defence with "
                 "exponential time decay (xi=0.0018), maxGoals=10",
        "source": {
            "actor": "commodus67/soccer-dixon-coles-match-predictor",
            "url": "https://apify.com/commodus67/soccer-dixon-coles-match-predictor",
            "seasonsBack": INPUT["seasonsBack"],
            "upcomingDays": INPUT["upcomingDays"],
        },
        "leagues": leagues,
    }
    DATA = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(HTML.replace("__DATA__", DATA))
    print("wrote %s: %d leagues, %d matches" % (OUT, len(leagues), total))


if __name__ == "__main__":
    main()
