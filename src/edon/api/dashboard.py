"""Dependency-free operational dashboard."""

DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>EDON Control Plane</title>
  <style>
    :root { color-scheme: dark; font-family: ui-sans-serif,system-ui,sans-serif; }
    body { margin:0; background:#0b1020; color:#e8edf7; }
    header { padding:24px 5vw; border-bottom:1px solid #25304a; display:flex; justify-content:space-between; }
    main { padding:24px 5vw; display:grid; gap:20px; }
    .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:14px; }
    .card, section { background:#121a2d; border:1px solid #283552; border-radius:12px; padding:18px; }
    .value { font-size:2rem; font-weight:700; color:#72e1b1; }
    table { width:100%; border-collapse:collapse; }
    th,td { text-align:left; border-bottom:1px solid #283552; padding:9px; font-size:.9rem; }
    input,button { background:#0d1425; color:#fff; border:1px solid #344463; border-radius:7px; padding:8px; }
    button { cursor:pointer; background:#235d4b; }
    .warning { color:#ffcc70; }
  </style>
</head>
<body>
<header><div><strong>EDON Control Plane</strong><div class="warning">Non-authoritative research runtime</div></div>
<div><input id="token" type="password" placeholder="API token"><button onclick="loadData()">Connect</button></div></header>
<main>
  <div class="cards" id="cards"></div>
  <section><h2>Candidates</h2><table><thead><tr><th>ID</th><th>Mechanism</th><th>Risk</th><th>Status</th></tr></thead><tbody id="candidates"></tbody></table></section>
  <section><h2>Approved mechanisms</h2><table><thead><tr><th>Mechanism</th><th>Version</th><th>Active</th><th>Artifact</th></tr></thead><tbody id="mechanisms"></tbody></table></section>
  <section><h2>Recent audit events</h2><table><thead><tr><th>#</th><th>Event</th><th>Entity</th><th>Hash</th></tr></thead><tbody id="audit"></tbody></table></section>
</main>
<script>
async function api(path){const token=document.getElementById('token').value;localStorage.edonToken=token;
 const r=await fetch(path,{headers:{Authorization:'Bearer '+token}});if(!r.ok)throw new Error(await r.text());return r.json();}
function rows(id,data,fields){document.getElementById(id).innerHTML=data.map(x=>'<tr>'+fields.map(f=>'<td>'+String(x[f]??'')+'</td>').join('')+'</tr>').join('');}
async function loadData(){try{const [s,c,m,a]=await Promise.all([api('/api/status'),api('/api/candidates'),api('/api/mechanisms'),api('/api/audit')]);
 document.getElementById('cards').innerHTML=Object.entries(s.counts).map(([k,v])=>`<div class="card"><div>${k}</div><div class="value">${v}</div></div>`).join('');
 rows('candidates',c.items,['candidate_id','mechanism_id','risk_class','status']);rows('mechanisms',m.items,['mechanism_id','version','active','artifact_sha256']);
 rows('audit',a.items.slice(-20).reverse(),['sequence','event_type','entity_id','event_hash']);}catch(e){alert(e.message)}}
document.getElementById('token').value=localStorage.edonToken||'';
</script></body></html>"""