document.addEventListener("click",function(e){if(e.target.closest&&e.target.closest(".btn,.tick,.st-chip,.btab a")&&navigator.vibrate){try{navigator.vibrate(8)}catch(x){}}},true);
window.CSRF=document.querySelector('meta[name=csrf-token]').content;
document.querySelectorAll('form').forEach(function(f){if((f.method||'').toLowerCase()==='post'&&!f.querySelector('[name=csrf_token]')){var i=document.createElement('input');i.type='hidden';i.name='csrf_token';i.value=window.CSRF;f.appendChild(i);}});
(function(){var p=location.pathname,best=null;document.querySelectorAll("aside a[href]:not(.hub)").forEach(function(a){var h=a.getAttribute("href").split("?")[0];if(h===p||(h!=="/app"&&h.length>1&&p.indexOf(h)===0)){if(!best||h.length>best.getAttribute("href").length)best=a;}});if(best){var bh=best.getAttribute("href");document.querySelectorAll("aside a[href=\""+bh+"\"]").forEach(function(a){a.classList.add("on");});}if(false)best.classList.add("on");})();
// ---------- sidebar headings are drop-downs (one open at a time): remember the open one, and open the one holding the current page ----------
(function(){
 var KEY="navOpen1",groups=document.querySelectorAll("aside details.ngrp"),cur="";
 try{cur=localStorage.getItem(KEY)||"";}catch(e){}
 var on=document.querySelector("aside details.ngrp a.on");if(on){var p=on.closest("details.ngrp");if(p)cur=p.dataset.g;}
 groups.forEach(function(d){d.open=(d.dataset.g===cur);});
 groups.forEach(function(d){d.addEventListener("toggle",function(){
  if(d.open&&!(document.getElementById("allq")&&document.getElementById("allq").value)){groups.forEach(function(o){if(o!==d&&o.open)o.open=false;});try{localStorage.setItem(KEY,d.dataset.g);}catch(e){}}
  else{try{if(localStorage.getItem(KEY)===d.dataset.g)localStorage.setItem(KEY,"");}catch(e){}}
 });});
})();
if('serviceWorker' in navigator){window.addEventListener('load',function(){navigator.serviceWorker.register('/sw.js').catch(function(){})});}
function switchWs(id){var f=document.createElement('form');f.method='post';f.action='/switch/'+id;var i=document.createElement('input');i.type='hidden';i.name='csrf_token';i.value=window.CSRF;f.appendChild(i);document.body.appendChild(f);f.submit();}
async function api(url,body){var r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':window.CSRF},body:JSON.stringify(body||{})});var d={};try{d=await r.json()}catch(e){}return {ok:r.ok,status:r.status,data:d};}

// ---------- top-bar dropdowns (help / notifications / profile) ----------
function toggleDD(btn){
 var menu=btn.nextElementSibling,open=menu.classList.contains('show');
 document.querySelectorAll('.dd-menu.show').forEach(function(m){m.classList.remove('show')});
 if(!open)menu.classList.add('show');
}
document.addEventListener('click',function(e){if(!e.target.closest('.dd'))document.querySelectorAll('.dd-menu.show').forEach(function(m){m.classList.remove('show')});});
var _notifsLoaded=false;
async function loadNotifs(){
 if(_notifsLoaded)return; _notifsLoaded=true;
 try{
  var r=await fetch('/notifications/recent');var d=await r.json();var box=document.getElementById('notifDD');
  if(!d.items||!d.items.length){box.innerHTML='<div class="muted" style="padding:10px">No notifications yet.</div>';return;}
  box.innerHTML=d.items.map(function(n){return '<a href="'+n.link+'" style="white-space:normal'+(n.is_read?'':';font-weight:600')+'">'+n.message+'<br><span class="muted" style="font-weight:400;font-size:11px">'+n.created_at+'</span></a>';}).join('')+'<a href="/notifications" style="text-align:center;border-top:1px solid var(--line)">See all →</a>';
 }catch(e){_notifsLoaded=false;}
}
// ---------- lightweight formatting helpers for long text fields (bold / italic / bullet list) ----------
function wrapSel(id,mark){
 var el=document.getElementById(id);if(!el)return;
 var s=el.selectionStart,e=el.selectionEnd,v=el.value;
 el.value=v.slice(0,s)+mark+v.slice(s,e)+mark+v.slice(e);
 el.focus();el.selectionStart=s+mark.length;el.selectionEnd=e+mark.length;
}
function bullets(id){
 var el=document.getElementById(id);if(!el)return;
 var s=el.selectionStart,e=el.selectionEnd,v=el.value;
 var sel=v.slice(s,e)||'List item';
 var lines=sel.split('\n').map(function(l){return l.trim()?'- '+l.replace(/^- /,''):l;}).join('\n');
 el.value=v.slice(0,s)+lines+v.slice(e);
 el.focus();
}


// ---------- search box: Ctrl/Cmd+K focuses it, Esc or the ✕ clears and closes it
(function(){var i=document.getElementById('tbq'),x=document.getElementById('tbclear'),k=document.getElementById('tbkbd');if(!i)return;
 function sync(){var has=i.value.length>0;if(x)x.hidden=!has;if(k)k.style.display=has||document.activeElement===i?'none':'';}
 i.addEventListener('input',sync);i.addEventListener('focus',sync);i.addEventListener('blur',sync);sync();
 if(x)x.addEventListener('click',function(){i.value='';sync();i.focus();if(location.pathname==='/search'&&/[?&]q=/.test(location.search))location.href='/search';});
 i.addEventListener('keydown',function(e){if(e.key==='Escape'){i.value='';i.blur();sync();}});
 document.addEventListener('keydown',function(e){if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();i.focus();i.select();}});
})();
// flash messages slide away on their own
window.toast=function(msg,ms){var c=document.querySelector(".toasts");if(!c){c=document.createElement("div");c.className="toasts";c.setAttribute("role","status");document.body.appendChild(c);}
 var f=document.createElement("div");f.className="flash";f.textContent=msg;var x=document.createElement("button");x.type="button";x.className="flash-x";x.setAttribute("aria-label","Dismiss");x.textContent="✕";x.onclick=function(){f.remove();};f.appendChild(x);c.appendChild(f);
 setTimeout(function(){f.classList.add("out");setTimeout(function(){f.remove();},400);},ms||3200);};
setTimeout(function(){document.querySelectorAll('.toasts .flash').forEach(function(f){f.classList.add('out');setTimeout(function(){f.remove();},400);});},6500);
// greeting on the dashboard uses the viewer's own clock
(function(){var g=document.getElementById('greet');if(!g)return;var h=new Date().getHours();g.textContent=h<5?'Burning the midnight oil':h<12?'Good morning':h<17?'Good afternoon':h<21?'Good evening':'Good night';})();

// ---------- UTM builder (pop-up form): live link + copy
function buildUtm(f){var b=(f.querySelector('#u_base_url')||{}).value||'';b=b.trim();var out=f.querySelector('#u_full_url');if(!out)return;if(!b){out.value='';return;}
 var p=new URLSearchParams();['source','medium','campaign','term','content'].forEach(function(k){var e=f.querySelector('#u_'+k);var v=e&&e.value.trim();if(v)p.set('utm_'+k,v.toLowerCase().replace(/\s+/g,'_'));});
 var q=p.toString();out.value=b+(q?(b.indexOf('?')>-1?'&':'?')+q:'');}
document.addEventListener('input',function(e){var f=e.target.closest&&e.target.closest('form[data-utm]');if(f)buildUtm(f);});
function copyText(btn){var t=btn.getAttribute('data-copy')||'';var done=function(){var o=btn.textContent;btn.textContent='Copied ✓';setTimeout(function(){btn.textContent=o;},1400);};
 try{navigator.clipboard.writeText(t).then(done,function(){});}catch(x){var a=document.createElement('textarea');a.value=t;document.body.appendChild(a);a.select();try{document.execCommand('copy');}catch(y){}a.remove();done();}}
function copyUtm(btn){var f=btn.closest('form'),v=f.querySelector('#u_full_url').value;if(!v){f.querySelector('#u_base_url').focus();return;}btn.setAttribute('data-copy',v);copyText(btn);}
// ---------- quick-add overlay: loads a form fragment via fetch and shows it in a pop-up dialog with a close (✕), instead of navigating away ----------
function _overlaySep(href){ return href.indexOf('?') === -1 ? '?' : '&'; }
function openOverlay(href, backTo){
 var d=document.getElementById('overlayModal'),body=document.getElementById('overlayBody');
 // wait for the form before opening the box, so nothing empty flashes on click; only a slow load shows a small spinner
 var slow=setTimeout(function(){ if(!d.open){ body.innerHTML='<div class="ov-load"><i></i></div>'; d.showModal(); } },700);
 fetch(href+_overlaySep(href)+'modal=1', {headers:{'X-Requested-With':'fetch'}}).then(function(r){return r.text();}).then(function(html){
  clearTimeout(slow);
  body.innerHTML=html;
  if(!d.open)d.showModal();  // calling showModal() while already open throws, so only open it once
  _bindOverlayForm(body);
 }).catch(function(){ clearTimeout(slow); body.innerHTML='<p class="muted" style="padding:20px">Could not load the form. <a href="'+href+'">Open it in a new page instead</a>.</p>'; if(!d.open)d.showModal(); });
 return false;
}
// every "+ New" / "Edit" link to a record form opens as a pop-up, everywhere in the app (lists, calendar, dashboard, team hub, search…)
document.addEventListener('click',function(e){
 if(e.defaultPrevented||e.button!==0||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey)return;
 var a=e.target.closest&&e.target.closest('a[href]'); if(!a||a.target==='_blank'||a.hasAttribute('download')||a.closest('#overlayBody a.nopop'))return;
 var u; try{u=new URL(a.href,location.href);}catch(x){return;}
 if(u.origin!==location.origin||!/^\/(m\/[a-z_]+\/(new|\d+\/edit)|utm\/new)$/.test(u.pathname))return;
 if(/^\/m\/[a-z_]+\/\d+\/edit$/.test(location.pathname)||/^\/m\/[a-z_]+\/new$/.test(location.pathname)||location.pathname==='/utm/new')return;  // already on a full form page
 e.preventDefault(); openOverlay(u.pathname+u.search,'');
});
function _bindOverlayForm(body){
 var form=body.querySelector('form');
 if(!form) return;
 form.addEventListener('submit', function(e){
  e.preventDefault();
  var fd=new FormData(form);
  if(!fd.get('csrf_token')) fd.set('csrf_token', window.CSRF);
  fetch(form.action, {method:'POST', body:fd, redirect:'manual', headers:{'X-CSRFToken':window.CSRF}}).then(function(r){
   if(r.type==='opaqueredirect' || r.status===0 || (r.status>=300 && r.status<400)){
    document.getElementById('overlayModal').close();
    location.reload();
   } else {
    return r.text().then(function(html){ body.innerHTML=html; _bindOverlayForm(body); });
   }
  }).catch(function(){ body.innerHTML='<p class="muted" style="padding:20px">Something went wrong saving this. Please try again.</p>'; });
 });
}
if(window.history && 'scrollRestoration' in history){try{history.scrollRestoration='manual';}catch(e){}}
// scroll: new pages start at the top; Back/Forward and "saved/deleted/ticked on the same list page" return you to where you were
(function(){
 var K=function(){return "sc:"+location.pathname+location.search;};
 function put(k,v){try{sessionStorage.setItem(k,v);}catch(e){}} function get(k){try{return sessionStorage.getItem(k);}catch(e){return null;}}
 window.addEventListener('pagehide',function(){put(K(),String(Math.round(window.scrollY)));});
 document.addEventListener('submit',function(e){var f=e.target;if(e.defaultPrevented)return;if((f.method||'').toLowerCase()==='post')put('scKeep',JSON.stringify({u:location.pathname+location.search,y:Math.round(window.scrollY),t:Date.now()}));},false);
 window.addEventListener('load',function(){
  document.body.classList.remove('nav-open');
  var y=0,nav=(performance.getEntriesByType&&performance.getEntriesByType('navigation')[0])||{};
  if(nav.type==='back_forward'){y=parseInt(get(K())||"0",10)||0;}
  else{var k=null;try{k=JSON.parse(get('scKeep')||"null");}catch(e){}
   if(k&&k.u===location.pathname+location.search&&Date.now()-k.t<15000)y=k.y||0;}
  try{sessionStorage.removeItem('scKeep');}catch(e){}
  if(location.hash&&!y)return;
  window.scrollTo({top:y,behavior:'instant'});
 });
})();

// ---------- first-time tour: a few spotlighted tips pointing at where things live ----------
var TOUR_STEPS=[
 {sel:"[data-tour=modules]",title:"Everything lives here",text:"Pick a hub on the left. Tap Search (or press Ctrl+K) to jump anywhere."},
 {sel:"[data-tour=create]",title:"Create",text:"Add content, a task, a lead or a campaign from anywhere."},
 {sel:"[data-tour=search]",title:"Search",text:"Find anything you saved. Ctrl+K gets you here fast."},
 {sel:"[data-tour=help]",title:"Stuck?",text:"Guides and the user manual are one tap away."}
];
function dismissTour(){
 var had=document.querySelectorAll('.tour-pop,.tour-mask').length>0;
 document.querySelectorAll('.tour-pop,.tour-mask').forEach(function(e){e.remove()});
 if(had)api('/account/onboarded',{});
}
// any dialog opening (quick-add overlay, a board's How-to-use, etc.) should clear the tour first, so the two never sit on screen together
if(window.HTMLDialogElement){
 var _showModal=HTMLDialogElement.prototype.showModal;
 HTMLDialogElement.prototype.showModal=function(){dismissTour();return _showModal.call(this);};
}
function tourStep(i){
 document.querySelectorAll('.tour-pop,.tour-mask').forEach(function(e){e.remove()});
 if(i>=TOUR_STEPS.length){api('/account/onboarded',{});return;}
 var st=TOUR_STEPS[i],el=document.querySelector(st.sel);
 if(!el){tourStep(i+1);return;}
 el.scrollIntoView({block:'center'});
 setTimeout(function(){
  var r=el.getBoundingClientRect();
  var mask=document.createElement('div');mask.className='tour-mask';
  mask.style.cssText='position:fixed;left:'+(r.left-6)+'px;top:'+(r.top-6)+'px;width:'+(r.width+12)+'px;height:'+(r.height+12)+'px;border-radius:10px;box-shadow:0 0 0 4000px rgba(43,36,66,.45),0 0 0 3px var(--pri);z-index:9998;pointer-events:none;transition:all .2s';
  document.body.appendChild(mask);
  var pop=document.createElement('div');pop.className='tour-pop';
  var top=Math.min(window.innerHeight-160,Math.max(10,r.bottom+12));
  var left=Math.min(window.innerWidth-300,Math.max(10,r.left));
  // never sit on top of the sidebar's own buttons (Idk what to do and Edit menu): put the card beside it on wide screens
  if(window.innerWidth>=900&&r.left<260){left=270;top=Math.max(70,r.top);}
  pop.style.cssText='position:fixed;left:'+left+'px;top:'+top+'px;max-width:280px;background:#fff;border-radius:12px;box-shadow:var(--shadow-lg);padding:14px 16px;z-index:9999;font-size:13px';
  pop.innerHTML='<b style="color:var(--pri-d)">'+st.title+'</b><p style="margin:6px 0 10px;color:var(--mut)">'+st.text+'</p><div style="display:flex;justify-content:space-between;align-items:center"><span class="muted" style="font-size:11px">'+(i+1)+' / '+TOUR_STEPS.length+'</span><span><button id="tourSkip" class="btn ghost sm" style="margin-right:6px">Skip</button><button id="tourNext" class="btn sm">'+(i+1<TOUR_STEPS.length?'Next':'Done')+'</button></span></div>';
  document.body.appendChild(pop);
  document.getElementById('tourNext').onclick=function(){tourStep(i+1);};
  document.getElementById('tourSkip').onclick=dismissTour;
 },250);
}
// a click on anything that is not the tour card means "I'm using the app": drop the tour so no button ever feels dead
document.addEventListener('click',function(e){if(document.querySelector('.tour-pop')&&!e.target.closest('.tour-pop'))dismissTour();},true);
function startTour(){if(document.querySelector('dialog[open]'))return;tourStep(0);}
if(__D.tour){window.addEventListener('load',function(){setTimeout(startTour,600);});}

// ---------- shorter sidebar: essentials + searchable All tools ----------
(function(){var p=location.pathname;document.querySelectorAll('.bnav a[href]').forEach(function(a){var h=a.getAttribute('href');if(h&&h!=='#'&&(h===p||(h.length>1&&p.indexOf(h)===0&&h!=='/')))a.classList.add('on')})})();



window.toggleSide=function(){if(innerWidth<=800){document.body.classList.toggle("nav-open");return;}var h=document.documentElement,off=h.classList.toggle("side-off");try{localStorage.setItem("sideOff",off?"1":"0");}catch(e){}var b=document.getElementById("sideBtn");if(b){b.setAttribute("aria-expanded",off?"false":"true");}};
(function(){var g=0,tm;document.addEventListener("keydown",function(e){if(e.ctrlKey||e.metaKey||e.altKey||document.querySelector("dialog[open]"))return;var t=e.target;if(t&&(/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName)||t.isContentEditable))return;var k=(e.key||"").toLowerCase();if(!document.body.classList.contains("app")||document.body.classList.contains("isdemo"))return;if(g){g=0;clearTimeout(tm);if(k==="c")location.href="/calendar";else if(k==="h")location.href="/app";return;}if(k==="g"){g=1;tm=setTimeout(function(){g=0},900);}else if(k==="n"){location.href="/m/content_items/new";}else if(k==="t"){location.href="/app";}});})();
document.addEventListener("keydown",function(e){if(e.key==="?"&&!e.ctrlKey&&!e.metaKey&&!e.altKey&&!document.querySelector("dialog[open]")){var t=e.target;if(t&&(/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName)||t.isContentEditable))return;if(location.pathname!=="/help")location.href="/help";return;}
if((e.ctrlKey||e.metaKey)&&!e.shiftKey&&!e.altKey&&e.key.toLowerCase()==="b"&&document.getElementById("sideBtn")){var t=e.target;if(t&&/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName)||t&&t.isContentEditable)return;e.preventDefault();toggleSide();}});
(function(){var b=document.getElementById("sideBtn");if(b&&document.documentElement.classList.contains("side-off"))b.setAttribute("aria-expanded","false");})();
window.TOOLS=__D.tools;window.HUBNOW=__D.hubnow;
// ---------- your menu: rename and reorder hubs (saved in this browser) + recently used tools ----------
(function(){var box=document.querySelector(".ess");if(!box)return;
 function get(k,d){try{return localStorage.getItem(k)||d;}catch(e){return d;}}
 function put(k,v){try{localStorage.setItem(k,v);}catch(e){}}
 var prefs={order:[],names:{},moves:{},tabOrder:{}};try{prefs=Object.assign(prefs,JSON.parse(get("hubPrefs","{}")));}catch(e){}
 var MENU_VER=3;if(prefs.ver!==MENU_VER){prefs={order:[],names:{},moves:{},tabOrder:{},ver:MENU_VER};try{put("hubPrefs",JSON.stringify(prefs));}catch(e){}}   // menu layout changed: drop menus saved by older versions once
 prefs.order=prefs.order||[];prefs.names=prefs.names||{};prefs.moves=prefs.moves||{};prefs.tabOrder=prefs.tabOrder||{};
 var NOW=window.HUBNOW||"";
 var hubs=function(){return [].slice.call(box.querySelectorAll("a.hub"));};
 var defaults={};hubs().forEach(function(a){defaults[a.dataset.hub]=a.dataset.label||a.textContent.trim().replace(/^\S+\s*/,"");});
 function labelOf(k){return prefs.names[k]||defaults[k]||k;}
 var BASE={},ORIG={};(window.TOOLS||[]).forEach(function(g){if(g.k){BASE[g.k]={i:g.i,items:g.items.map(function(x){return x.slice();})};g.items.forEach(function(x){ORIG[x[1]]=g.k;});}});
 function esc(v){return String(v).replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/</g,"&lt;");}
 function layout(){var L={},ks=Object.keys(BASE);ks.forEach(function(k){L[k]=[];});
  ks.forEach(function(k){BASE[k].items.forEach(function(x){var t=prefs.moves[x[1]];if(!t||!L[t]||t===k)L[k].push(x);});});
  ks.forEach(function(k){BASE[k].items.forEach(function(x){var t=prefs.moves[x[1]];if(t&&L[t]&&t!==k)L[t].push(x);});});
  ks.forEach(function(k){var o=prefs.tabOrder[k]||[];L[k].sort(function(a,b){var ia=o.indexOf(a[1]),ib=o.indexOf(b[1]);if(ia<0&&ib<0)return 0;if(ia<0)return 1;if(ib<0)return -1;return ia-ib;});});
  return L;}
 function custom(){return Object.keys(prefs.moves).length||Object.keys(prefs.tabOrder).length||Object.keys(prefs.names).length;}
 function buildBar(L){var slot=document.getElementById("hubSlot");if(!slot||!NOW||!custom())return;
  var k=null;Object.keys(L).forEach(function(h){if(L[h].some(function(x){return x[1]===NOW;}))k=h;});
  var old=document.querySelector(".hubtabs");if(old)old.remove();if(!k||L[k].length<2)return;
  var nav=document.createElement("nav");nav.className="hubtabs";nav.dataset.hub=k;nav.setAttribute("aria-label",labelOf(k)+" sections");
  var ti=document.createElement("span");ti.className="ht-title";ti.appendChild(document.createTextNode((BASE[k].i||"")+" "));var nm=document.createElement("span");nm.className="ht-name";nm.textContent=labelOf(k);ti.appendChild(nm);
  var row=document.createElement("div");row.className="ht-row";
  L[k].forEach(function(x){var a=document.createElement("a");a.className="ht"+(x[1]===NOW?" on":"");a.href=x[1];a.textContent=x[0];if(x[1]===NOW)a.setAttribute("aria-current","page");row.appendChild(a);});
  nav.appendChild(ti);nav.appendChild(row);slot.parentNode.insertBefore(nav,slot);}
 function apply(){var L=layout(),anchor=box.querySelector("#hubEnd"),list=hubs();
  var ord=prefs.order.filter(function(k){return list.some(function(a){return a.dataset.hub===k;});});
  list.sort(function(a,b){var ia=ord.indexOf(a.dataset.hub),ib=ord.indexOf(b.dataset.hub);if(ia<0&&ib<0)return 0;if(ia<0)return 1;if(ib<0)return -1;return ia-ib;});
  list.forEach(function(a){anchor.parentNode.insertBefore(a,anchor);var k=a.dataset.hub,t=a.querySelector(".hl"),it=L[k]||[];if(t)t.textContent=labelOf(k);
   a.dataset.empty=it.length?"":"1";if(it.length)a.setAttribute("href",it[0][1]);
   if(NOW)a.classList.toggle("on",it.some(function(x){return x[1]===NOW;}));});
  (window.TOOLS||[]).forEach(function(g){if(!g.k)return;g.g=labelOf(g.k);g.items=(L[g.k]||[]).map(function(x){return x.slice();});});
  buildBar(L);enhance();}
 // ---- reorder tabs right on the tab bar: drag a tab, or tap ⇄ and use ◀ ▶ (works on phones too)
 var reorder=false;
 function barOrder(nav){return [].slice.call(nav.querySelectorAll("a.ht")).map(function(a){return a.getAttribute("href");});}
 function moveTab(nav,href,to){var k=nav.dataset.hub,hs=barOrder(nav),i=hs.indexOf(href);if(i<0)return;hs.splice(i,1);hs.splice(Math.max(0,Math.min(hs.length,to)),0,href);prefs.tabOrder[k]=hs;save();apply();applySize();var f=document.querySelector('.hubtabs a.ht[href="'+href+'"] .ht-mv button');if(f&&reorder)try{f.focus();}catch(e){}}
 function enhance(){var nav=document.querySelector(".hubtabs");if(!nav)return;var row=nav.querySelector(".ht-row"),title=nav.querySelector(".ht-title");
  if(!nav.querySelector(".ht-edit")){var eb=document.createElement("button");eb.type="button";eb.className="ht-edit";eb.title="Change the order of these tabs";eb.setAttribute("aria-label","Reorder tabs");eb.textContent="⇄ Reorder";eb.addEventListener("click",function(){reorder=!reorder;apply();});nav.appendChild(eb);}
  var eb2=nav.querySelector(".ht-edit");eb2.setAttribute("aria-pressed",reorder?"true":"false");eb2.textContent=reorder?"✓ Done":"⇄ Reorder";nav.classList.toggle("reorder",reorder);
  var tabs=[].slice.call(nav.querySelectorAll("a.ht"));
  tabs.forEach(function(a,i){var old=a.querySelector(".ht-mv");if(old)old.remove();
   if(reorder){var m=document.createElement("span");m.className="ht-mv";[["◀","Move this tab left",-1],["▶","Move this tab right",1]].forEach(function(d){var b=document.createElement("button");b.type="button";b.textContent=d[0];b.setAttribute("aria-label",d[1]);b.title=d[1];if((d[2]<0&&i===0)||(d[2]>0&&i===tabs.length-1))b.disabled=true;
     b.addEventListener("click",function(e){e.preventDefault();e.stopPropagation();moveTab(nav,a.getAttribute("href"),i+d[2]);});m.appendChild(b);});a.appendChild(m);}
   if(!a.dataset.dnd){a.dataset.dnd="1";a.draggable=true;
    a.addEventListener("dragstart",function(e){e.dataTransfer.setData("text/plain",a.getAttribute("href"));e.dataTransfer.effectAllowed="move";a.classList.add("dragging");});
    a.addEventListener("dragend",function(){a.classList.remove("dragging");[].forEach.call(nav.querySelectorAll(".dropat"),function(x){x.classList.remove("dropat");});});
    a.addEventListener("dragover",function(e){e.preventDefault();e.dataTransfer.dropEffect="move";a.classList.add("dropat");});
    a.addEventListener("dragleave",function(){a.classList.remove("dropat");});
    a.addEventListener("drop",function(e){e.preventDefault();a.classList.remove("dropat");var h=e.dataTransfer.getData("text/plain"),hs=barOrder(nav),to=hs.indexOf(a.getAttribute("href"));if(h&&h!==a.getAttribute("href"))moveTab(nav,h,to);});}});}
 function save(){put("hubPrefs",JSON.stringify(prefs));}
 function applySize(){hubs().forEach(function(a){a.hidden=a.dataset.empty==="1";});}   // every hub is always listed
 // ---- the menu editor: rename hubs, reorder hubs and tabs, move any tab to any hub
 function dlg(){var d=document.getElementById("menuDlg");if(!d){d=document.createElement("dialog");d.id="menuDlg";d.className="menudlg";d.setAttribute("aria-label","Edit menu");document.body.appendChild(d);
  d.addEventListener("click",function(e){var t=e.target;if(t===d){d.close();return;}var b=t.closest("button[data-a]");if(!b)return;act(b.dataset.a,b);});
  d.addEventListener("change",function(e){var t=e.target;if(t.classList.contains("md-name")){var k=t.closest(".md-hub").dataset.k,v=t.value.trim();if(!v||v===defaults[k])delete prefs.names[k];else prefs.names[k]=v;commit();}
   else if(t.classList.contains("md-mv")&&t.value){var h=t.closest("li").dataset.h;if(t.value===ORIG[h])delete prefs.moves[h];else prefs.moves[h]=t.value;var L=layout(),tg=L[t.value].map(function(x){return x[1];}).filter(function(x){return x!==h;});tg.push(h);prefs.tabOrder[t.value]=tg;commit();}});
  d.addEventListener("keydown",function(e){if(e.key==="Enter"&&e.target.classList.contains("md-name")){e.preventDefault();e.target.blur();}});}
  return d;}
 function commit(){save();apply();applySize();render();}
 function render(){var d=dlg(),L=layout(),keys=hubs().map(function(a){return a.dataset.hub;}),sc=d.querySelector(".md-body"),top=sc?sc.scrollTop:0;
  var h='<div class="md-head"><b>✎ Edit menu</b><button type="button" class="md-x" data-a="done" aria-label="Close">✕</button></div><p class="muted md-help">Rename a hub, put hubs and tabs in your order with ▲ ▼, or move a tab to a different hub. Changes show straight away and are saved in this browser.</p><div class="md-body">';
  keys.forEach(function(k,hi){var it=L[k]||[];
   h+='<section class="md-hub" data-k="'+esc(k)+'"><div class="md-hrow"><span class="md-ic" aria-hidden="true">'+esc((BASE[k]||{}).i||"")+'</span><input class="md-name" maxlength="28" value="'+esc(labelOf(k))+'" aria-label="Hub name"><span class="md-btns"><button type="button" data-a="hup" aria-label="Move hub up"'+(hi?'':' disabled')+'>▲</button><button type="button" data-a="hdn" aria-label="Move hub down"'+(hi===keys.length-1?' disabled':'')+'>▼</button></span></div><ul class="md-tabs">';
   it.forEach(function(x,ti){h+='<li data-h="'+esc(x[1])+'"><span class="md-t">'+esc(x[0])+'</span><span class="md-btns"><button type="button" data-a="tup" aria-label="Move tab up"'+(ti?'':' disabled')+'>▲</button><button type="button" data-a="tdn" aria-label="Move tab down"'+(ti===it.length-1?' disabled':'')+'>▼</button><select class="md-mv" aria-label="Move this tab to another hub"><option value="">Move to…</option>'+keys.filter(function(q){return q!==k;}).map(function(q){return '<option value="'+esc(q)+'">'+esc(labelOf(q))+'</option>';}).join("")+'</select></span></li>';});
   if(!it.length)h+='<li class="md-empty">Nothing here yet. Move a tab in from another hub.</li>';
   h+='</ul></section>';});
  h+='</div><div class="md-foot"><button type="button" class="btn ghost sm" data-a="reset">↺ Reset everything</button><button type="button" class="btn sm" data-a="done">Done</button></div>';
  d.innerHTML=h;var nb=d.querySelector(".md-body");if(nb)nb.scrollTop=top;}
 function swap(a,i,j){if(j<0||j>=a.length)return;var t=a[i];a[i]=a[j];a[j]=t;}
 function act(a,b){var d=dlg();
  if(a==="done"){d.close();return;}
  if(a==="reset"){prefs={order:[],names:{},moves:{},tabOrder:{}};save();location.reload();return;}
  if(a==="hup"||a==="hdn"){var k=b.closest(".md-hub").dataset.k,ks=hubs().map(function(x){return x.dataset.hub;}),i=ks.indexOf(k);swap(ks,i,a==="hup"?i-1:i+1);prefs.order=ks;commit();return;}
  if(a==="tup"||a==="tdn"){var hk=b.closest(".md-hub").dataset.k,hr=b.closest("li").dataset.h,hs=layout()[hk].map(function(x){return x[1];}),j=hs.indexOf(hr);swap(hs,j,a==="tup"?j-1:j+1);prefs.tabOrder[hk]=hs;commit();}}
 var btn=document.getElementById("hubEdit");
 if(btn)btn.addEventListener("click",function(){var d=dlg();render();if(d.showModal)d.showModal();else d.setAttribute("open","");var f=d.querySelector(".md-name");if(f)f.focus();});
 apply();applySize();
 // recent: remember the last few tool pages visited and show them as quick chips
 var rr=document.getElementById("recentRow");if(!rr)return;
 var p=location.pathname,isTool=/^\/(m\/[a-z_]+|calendar|moodboards|ideas|ai|analytics|pulse|discover|utm|report)\/?$/.test(p)||/^\/m\/[a-z_]+$/.test(p);
 var list=[];try{list=JSON.parse(get("recentTools","[]"))||[];}catch(e){list=[];}
 var h=document.querySelector(".head h1");
 if(isTool&&h){var label=h.textContent.trim().replace(/\s+/g," ").slice(0,28);list=list.filter(function(x){return x.h!==p;});list.unshift({h:p,l:label});list=list.slice(0,4);try{localStorage.setItem("recentTools",JSON.stringify(list));}catch(e){}}
 var shown=list.filter(function(x){return x.h!==p;}).slice(0,2);
 if(shown.length){rr.hidden=false;rr.className="recent";rr.innerHTML="<small>Recent</small>";shown.forEach(function(x){var a=document.createElement("a");a.href=x.h;a.textContent=x.l;rr.appendChild(a);});}
})();


// ---------- tool finder: every page lives in the search bar, not in the sidebar ----------
var TOOLS=window.TOOLS;
function openFinder(grp,el){var F=document.getElementById("finder");if(!F)return;window.__fgroup=grp||"";var tb=document.getElementById("tbq");if(grp){document.body.classList.remove("nav-open");F.openIn(window.innerWidth>800?"side":"sheet",el);return;}if(tb&&tb.offsetParent){tb.focus();tb.select();}else{document.body.classList.remove("nav-open");F.openIn("sheet");}}
(function(){var F=document.getElementById("finder");if(!F)return;
 var L=document.getElementById("fl"),FQ=document.getElementById("fq"),TB=document.getElementById("tbq"),mode="",sel=-1;
 function esc(t){return String(t).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}
 function pins(){try{return window.__pins?window.__pins():[];}catch(e){return [];}}
 function render(t){t=(t||"").trim().toLowerCase();var h="",n=0,p=pins();
  if(t)h+='<a class="fr fr-s" href="/search?q='+encodeURIComponent(t)+'">🔎 <span>Search all your items for “'+esc(t)+'”</span></a>';
  (window.TOOLS||[]).forEach(function(g){if(window.__fgroup&&g.g!==window.__fgroup)return;var rows=g.items.filter(function(x){return !t||(x[0]+" "+g.g).toLowerCase().indexOf(t)>-1;});if(!rows.length)return;
   h+='<div class="fg">'+g.i+" "+esc(g.g)+"</div>";
   rows.forEach(function(x){n++;var on=p.indexOf(x[1])>-1;h+='<div class="fr-w"><a class="fr" href="'+x[1]+'">'+esc(x[0])+'</a><button type="button" class="fpin'+(on?" on":"")+'" data-h="'+x[1]+'" aria-label="'+(on?"Unpin":"Pin")+' this page">'+(on?"★":"☆")+"</button></div>";});});
  if(!n&&t)h+='<p class="muted fnone">No tool by that name. Press Enter to search all your items instead.</p>';
  var ti=document.getElementById("fndTitle");if(ti)ti.textContent=window.__fgroup?"← "+window.__fgroup:"🔎 All tools";L.innerHTML=h;sel=-1;}
 function place(){if(mode!=="desk"||!TB)return;var r=TB.closest("form").getBoundingClientRect();F.style.top=(r.bottom+8)+"px";F.style.right=Math.max(12,window.innerWidth-r.right-40)+"px";F.style.left="auto";}
 function openIn(m,el){mode=m;F.className="fnd-"+m;F.hidden=false;
  if(m==="desk"){window.__fgroup="";place();render(TB.value);}
  else if(m==="side"){var r=el.getBoundingClientRect();F.style.cssText="top:"+Math.max(64,Math.min(r.top-10,window.innerHeight-420))+"px;left:"+(r.right+10)+"px;right:auto";FQ.value="";render("");}
  else{F.style.cssText="";if(!window.__fgroup)FQ.value=FQ.value;render(FQ.value);if(!window.__fgroup)setTimeout(function(){FQ.focus();},30);}}
 function close(){F.hidden=true;sel=-1;}
 F.openIn=openIn;
 function rows(){return [].slice.call(L.querySelectorAll("a.fr"));}
 function move(d){var r=rows();if(!r.length)return;sel=(sel+d+r.length)%r.length;r.forEach(function(a,i){a.classList.toggle("sel",i===sel);});r[sel].scrollIntoView({block:"nearest"});}
 function key(e,inp){if(e.key==="ArrowDown"){e.preventDefault();move(1);}else if(e.key==="ArrowUp"){e.preventDefault();move(-1);}else if(e.key==="Escape"){close();}
  else if(e.key==="Enter"){var r=rows();if(sel>-1&&r[sel]){e.preventDefault();location.href=r[sel].getAttribute("href");}else if(inp===FQ){e.preventDefault();var f=r.filter(function(a){return !a.classList.contains("fr-s");})[0]||r[0];if(f)location.href=f.getAttribute("href");}}}
 if(TB){TB.addEventListener("focus",function(){openIn("desk");});TB.addEventListener("click",function(){if(F.hidden)openIn("desk");});TB.addEventListener("input",function(){if(F.hidden)openIn("desk");render(TB.value);});TB.addEventListener("keydown",function(e){key(e,TB);});window.addEventListener("resize",place);}
 FQ.addEventListener("input",function(){window.__fgroup="";render(FQ.value);});FQ.addEventListener("keydown",function(e){key(e,FQ);});
 F.querySelector(".fnd-x").addEventListener("click",close);
 var tt=document.getElementById("fndTitle");if(tt)tt.addEventListener("click",function(){if(window.__fgroup){window.__fgroup="";render(FQ.value);}});
 F.addEventListener("click",function(e){var b=e.target.closest(".fpin");if(b){e.preventDefault();if(window.__togglePin)window.__togglePin(b.dataset.h);var on=pins().indexOf(b.dataset.h)>-1;b.classList.toggle("on",on);b.textContent=on?"★":"☆";return;}if(e.target.closest("a.fr"))close();});
 document.addEventListener("keydown",function(e){if(e.key==="Escape"&&!F.hidden)close();});
 document.addEventListener("mousedown",function(e){if(F.hidden)return;if(e.target.closest("#finder")||e.target.closest(".tb-search")||e.target.closest("#allBtn")||e.target.closest(".gtile"))return;close();});
})();

// ---------- dark mode, pinned pages, confetti ----------

// ---------- Pick your vibe: a palette of two colours, in rich or soft tones; works in light and dark ----------
var VP=__D.vp;
function vmRows(){var t=document.getElementById('vmTheme'),s=document.getElementById('vmSnd');if(t)t.textContent=document.documentElement.getAttribute('data-theme')==='dark'?'☀️ Light mode':'🌙 Dark mode';if(s)s.textContent=soundOn()?'🔊 Sound on':'🔇 Sound off';}
function openVibes(btn){
  var m=document.getElementById("vibeMenu");
  if(m){var open=!m.hidden;m.hidden=open;if(btn&&btn.setAttribute)btn.setAttribute("aria-expanded",open?"false":"true");if(!open){markVibe();vmRows();}return;}
  m=document.createElement("div");m.id="vibeMenu";m.className="vibemenu";m.setAttribute("role","dialog");m.setAttribute("aria-label","Pick your vibe");
  var h='<div class="vm-head"><b>Pick your vibe</b><button type="button" class="vm-x" aria-label="Close" onclick="openVibes()">✕</button></div><div class="vm-row"><button type="button" class="vm-tog" id="vmTheme" onclick="toggleTheme();vmRows()"></button><button type="button" class="vm-tog" id="vmSnd" onclick="toggleSound();vmRows()"></button></div><p class="vm-sub">Two colours, your whole app. Works in light and dark.</p>';
  h+='<button type="button" class="vm-auto" data-k="auto" onclick="setVibe(\'auto\')"><i class="vm-sw vm-auto-sw"></i> Auto <small>your workspace colours</small></button>';
  [["rich","Rich and deep"],["soft","Soft and light"]].forEach(function(t){
    h+='<div class="vm-h">'+t[1]+'</div><div class="vm-grid">';
    VP.filter(function(p){return p[5]===t[0]}).forEach(function(p){h+='<button type="button" class="vm-b" data-k="'+p[0]+'" aria-label="'+p[1]+' '+t[0]+'" title="'+p[1]+'" onclick="setVibe(\''+p[0]+'\')"><i class="vm-sw" style="background:linear-gradient(135deg,'+p[2]+' 0 50%,'+p[3]+' 50% 100%)"></i><span>'+p[1]+'</span></button>'});
    h+='</div>';});
  m.innerHTML=h;document.body.appendChild(m);markVibe();vmRows();
  if(btn&&btn.setAttribute)btn.setAttribute("aria-expanded","true");
  document.addEventListener("click",function(e){var mm=document.getElementById("vibeMenu");if(mm&&!mm.hidden&&!mm.contains(e.target)&&!e.target.closest("#vibeBtn,.dd-snd")){mm.hidden=true;var b=document.getElementById("vibeBtn");if(b)b.setAttribute("aria-expanded","false");}});
  document.addEventListener("keydown",function(e){if(e.key==="Escape"){var mm=document.getElementById("vibeMenu");if(mm&&!mm.hidden){mm.hidden=true;var b=document.getElementById("vibeBtn");if(b){b.setAttribute("aria-expanded","false");b.focus();}}}});
}
function markVibe(){var cur=document.documentElement.getAttribute("data-pal")||"auto";document.querySelectorAll("#vibeMenu [data-k]").forEach(function(b){b.classList.toggle("on",b.getAttribute("data-k")===cur);b.setAttribute("aria-pressed",b.getAttribute("data-k")===cur?"true":"false");});}
function setVibe(k){
  if(k==="auto")document.documentElement.removeAttribute("data-pal");else document.documentElement.setAttribute("data-pal",k);
  markVibe();try{chime&&chime()}catch(e){}
  api("/pal",{pal:k});
}
function ico(n){return '<i class="ic ic-'+n+'" aria-hidden="true"></i>';}
function inApp(){return !document.body.classList.contains("pub");}
function setThemeIcon(){var d=document.documentElement.getAttribute("data-theme")==="dark";document.querySelectorAll(".tb-theme").forEach(function(x){x.innerHTML=inApp()?(d?"☀️":"🌙"):ico(d?"sun":"moon");});}
function toggleTheme(){var d=document.documentElement.getAttribute("data-theme")==="dark";if(d)document.documentElement.removeAttribute("data-theme");else document.documentElement.setAttribute("data-theme","dark");try{localStorage.setItem("theme",d?"light":"dark");}catch(e){}setThemeIcon();}
function soundOn(){try{return localStorage.getItem("sound")==="on";}catch(e){return false;}}
function setSndIcon(){document.querySelectorAll(".tb-snd").forEach(function(x){x.innerHTML=inApp()?(soundOn()?"🔊":"🔇"):ico(soundOn()?"vol":"mute");x.setAttribute("aria-pressed",soundOn()?"true":"false");});}
function toggleSound(){var on=soundOn();try{localStorage.setItem("sound",on?"off":"on");}catch(e){}setSndIcon();if(on&&window.speechSynthesis)speechSynthesis.cancel();else cheer("Sound is on");}
var _ac=null;
function chime(){try{var A=window.AudioContext||window.webkitAudioContext;if(!A)return;_ac=_ac||new A();var t=_ac.currentTime;[523.25,659.25,783.99].forEach(function(f,i){var o=_ac.createOscillator(),g=_ac.createGain();o.type="sine";o.frequency.value=f;g.gain.setValueAtTime(0.0001,t+i*0.09);g.gain.exponentialRampToValueAtTime(0.18,t+i*0.09+0.02);g.gain.exponentialRampToValueAtTime(0.0001,t+i*0.09+0.35);o.connect(g);g.connect(_ac.destination);o.start(t+i*0.09);o.stop(t+i*0.09+0.4);});}catch(e){}}
var CHEERS=["Done. Nice one.","Task complete. Crushed it.","Ticked off. Keep going.","That's a win."];
function cheer(line){if(!soundOn())return;chime();try{if(window.speechSynthesis&&"SpeechSynthesisUtterance" in window){speechSynthesis.cancel();var u=new SpeechSynthesisUtterance(line||CHEERS[Math.floor(Math.random()*CHEERS.length)]);u.rate=1.05;u.pitch=1.1;u.volume=0.9;speechSynthesis.speak(u);}}catch(e){}}
setThemeIcon();setSndIcon();
/* phone gestures: swipe a task right to tick it off */
(function(){if(!("ontouchstart" in window))return;var row=null,x0=0,y0=0,dx=0;
document.addEventListener("touchstart",function(e){var r=e.target.closest&&e.target.closest(".trow");if(!r||e.target.closest("a,button,input,select,textarea")||!r.querySelector(".tick")){row=null;return;}row=r;var t=e.touches[0];x0=t.clientX;y0=t.clientY;dx=0;},{passive:true});
document.addEventListener("touchmove",function(e){if(!row)return;var t=e.touches[0];dx=t.clientX-x0;if(Math.abs(t.clientY-y0)>40){row.style.transform="";row=null;return;}row.style.transform="translateX("+Math.max(-120,Math.min(dx,120))+"px)";row.classList.toggle("swipe-ok",dx>90);row.classList.toggle("swipe-snooze",dx<-90);},{passive:true});
document.addEventListener("touchend",function(){if(!row)return;var r=row,ok=dx>90;row=null;r.style.transform="";r.classList.remove("swipe-ok");if(ok&&!r.classList.contains("done")){var b=r.querySelector(".tick");if(b)b.click();}},{passive:true});})();
/* skeleton on slow navigation instead of a blank wait */
(function(){var tm=null;document.addEventListener("click",function(e){var a=e.target.closest&&e.target.closest("a[href]");if(!a||a.target||e.defaultPrevented||e.metaKey||e.ctrlKey||e.shiftKey)return;var h=a.getAttribute("href")||"";if(!h||h.charAt(0)==="#"||h.indexOf("javascript:")===0||a.hasAttribute("download")||a.hasAttribute("onclick"))return;if(a.origin&&a.origin!==location.origin)return;clearTimeout(tm);tm=setTimeout(function(){document.body.classList.add("navigating");},180);});
window.addEventListener("pageshow",function(){clearTimeout(tm);document.body.classList.remove("navigating");});})();
function confetti(){if(window.matchMedia&&matchMedia("(prefers-reduced-motion: reduce)").matches)return;var cs=["#7c5cd6","#ff6b9d","#ffd60a","#2ec4b6","#ff9f1c","#4cc9f0"];for(var i=0;i<70;i++){var e=document.createElement("i");e.className="confetti-bit";e.style.left=(Math.random()*100)+"vw";e.style.background=cs[i%cs.length];e.style.setProperty("--dx",((Math.random()-.5)*240)+"px");e.style.setProperty("--rot",(Math.random()*720)+"deg");e.style.animationDelay=(Math.random()*.4)+"s";document.body.appendChild(e);setTimeout(function(x){x.remove();},2600,e);}}
(function(){var f=document.querySelector(".toasts .flash");if(f&&f.textContent.indexOf("🎉")>-1){confetti();cheer((f.textContent||"").replace(/[^A-Za-z0-9 ,.!']/g," ").replace(/\s+/g," ").trim().slice(0,90));}})();
/* Deb: eyes follow the pointer, click for a greeting, shy at passwords, shakes on a login error */
(function(){var debs=[].slice.call(document.querySelectorAll(".deb"));if(!debs.length)return;
var HI=["Hi, I'm Deb. Let's plan something great.","Hey you. Ready to launch?","Psst. Your calendar misses you.","You've got this."];
debs.forEach(function(d){if(!d.closest(".dhero,.hero,.authbox,.empty-state,.lp-bg"))return;d.style.cursor="pointer";d.setAttribute("tabindex","0");d.addEventListener("click",function(){d.classList.remove("deb-hop");void d.getBoundingClientRect();d.classList.add("deb-hop");setTimeout(function(){d.classList.remove("deb-hop");},700);confetti();cheer(HI[Math.floor(Math.random()*HI.length)]);});});
if(window.matchMedia&&matchMedia("(pointer:fine)").matches)document.addEventListener("pointermove",function(e){debs.forEach(function(d){var r=d.getBoundingClientRect();if(!r.width||r.bottom<0||r.top>innerHeight)return;var dx=Math.max(-1,Math.min(1,(e.clientX-(r.left+r.width/2))/300)),dy=Math.max(-1,Math.min(1,(e.clientY-(r.top+r.height/2))/300));d.querySelectorAll(".deb-eye,.deb-glint").forEach(function(el){el.style.translate=(dx*3)+"px "+(dy*2.5)+"px";});});});
var pw=document.querySelector("input[type=password]");if(pw){pw.addEventListener("focus",function(){debs.forEach(function(d){d.classList.add("deb-shy");});});pw.addEventListener("blur",function(){debs.forEach(function(d){d.classList.remove("deb-shy");});});}
var fl=document.querySelector(".authbox ~ .toasts .flash, .toasts .flash");if(fl&&document.querySelector(".authbox")){debs.forEach(function(d){d.classList.add("deb-shake");});cheer((fl.textContent||"Hmm, that didn't work.").replace(/\s+/g," ").trim().slice(0,90));}})();
/* milestone: streak celebrations */
(function(){var c=document.querySelector(".dhero");if(!c)return;var m=(c.textContent||"").match(/(\d+)-day streak/);if(!m)return;var n=+m[1];if([3,7,14,30,50,100].indexOf(n)<0)return;var k="streak"+n;try{if(localStorage.getItem(k))return;localStorage.setItem(k,"1");}catch(e){}setTimeout(function(){confetti();cheer(n+"-day streak. You are on fire.");},600);})();

/* web push */
function b64u(s){var p="=".repeat((4-s.length%4)%4),b=(s+p).replace(/-/g,"+").replace(/_/g,"/"),r=atob(b),o=new Uint8Array(r.length);for(var i=0;i<r.length;i++)o[i]=r.charCodeAt(i);return o}
function enablePush(){var m=document.getElementById("pushMsg");function say(t){if(m)m.textContent=t}
 fetch("/push/key").then(function(r){return r.json()}).then(function(d){if(!d.key){say("Push is not set up on this server yet.");return}
  return Notification.requestPermission().then(function(p){if(p!=="granted"){say("Notifications are blocked. Allow them in your browser settings.");return}
   return navigator.serviceWorker.ready.then(function(reg){return reg.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:b64u(d.key)})}).then(function(sub){
    return fetch("/push/subscribe",{method:"POST",headers:{"Content-Type":"application/json","X-CSRFToken":window.CSRF},body:JSON.stringify(sub)}).then(function(){say("You're in! We'll ping you.");var b=document.getElementById("pushBtn");if(b)b.hidden=true})})})}).catch(function(){say("Couldn't turn on push on this device.")})}
(function(){var c=document.getElementById("pushCard");if(!c||!("serviceWorker" in navigator)||!("PushManager" in window))return;
 fetch("/push/key").then(function(r){return r.json()}).then(function(d){if(!d.key)return;navigator.serviceWorker.ready.then(function(reg){return reg.pushManager.getSubscription()}).then(function(s){if(!s||Notification.permission!=="granted")c.hidden=false})}).catch(function(){})})();
// ---------- keep the sidebar scrolled to where you were across page loads. Runs AFTER the groups/All-tools panel have opened (otherwise the panel is still collapsed, the saved position gets clamped to 0 and the sidebar "slides up") ----------
(function(){
 var aside=document.querySelector("aside");if(!aside||__D.client)return;
 var ready=false,want=0;
 try{var saved=sessionStorage.getItem("asideScroll");if(saved!==null)want=parseInt(saved,10)||0;}catch(e){}
 function apply(){aside.scrollTop=want;}
 apply();requestAnimationFrame(apply);
 window.addEventListener("load",function(){apply();setTimeout(function(){apply();ready=true;},250);});
 var save=function(){if(!ready)return;try{sessionStorage.setItem("asideScroll",String(aside.scrollTop));}catch(e){}};
 aside.addEventListener("scroll",save,{passive:true});
 aside.addEventListener("click",function(e){if(e.target.closest("a")){ready=true;try{sessionStorage.setItem("asideScroll",String(aside.scrollTop));}catch(x){}}});
 window.addEventListener("pagehide",function(){if(ready)save();});
})();
/* tab title: name the page so tabs and history are not all just the app name */
(function(){var n=document.title.trim(),app=__D.app;if(n!==app)return;var h=document.querySelector("main h1,.page h1,h1");if(!h)return;
 var t=h.textContent.replace(/\s+/g," ").replace(/^[^A-Za-z0-9]+/,"").trim();if(t&&t.length<70)document.title=t+" · "+app;})();
/* instant (no-reload) tick-offs and reactions */
function fd(f){var d=new FormData(f);d.set("csrf_token",window.CSRF);return d}
document.addEventListener("submit",function(e){var f=e.target;
 var row=f.closest&&f.closest(".trow");
 if(row&&f.querySelector(".tick")&&f.querySelector("[name=value]")){e.preventDefault();var v=f.querySelector("[name=value]"),done=!row.classList.contains("done");
  row.classList.toggle("done",done);var t=f.querySelector(".tick"),body=fd(f);t.textContent=done?"✓":"";v.value=done?"To do":"Done";if(done){confetti();cheer();}
  fetch(f.action,{method:"POST",body:body,headers:{"X-CSRFToken":window.CSRF},credentials:"same-origin"}).then(function(r){if(!r.ok)throw 0}).catch(function(){row.classList.toggle("done",!done);t.textContent=done?"":"✓";v.value=done?"Done":"To do"});return}
 var rb=f.closest&&f.closest(".react-bar");
 if(rb){var b=f.querySelector(".react");if(!b)return;e.preventDefault();var mine=b.classList.toggle("mine"),c=b.querySelector("b");
  var n=(parseInt(c&&c.textContent)||0)+(mine?1:-1);if(c){c.textContent=n>0?n:""}else if(n>0){c=document.createElement("b");c.textContent=n;b.appendChild(c)}
  fetch(f.action,{method:"POST",body:fd(f),headers:{"X-CSRFToken":window.CSRF},credentials:"same-origin"}).catch(function(){})}
});

(function(){
 var aside=document.querySelector("aside");if(!aside)return;
 var KEY="pinnedPages",pins=[];try{pins=JSON.parse(localStorage.getItem(KEY)||"[]");}catch(e){}
 function save(){try{localStorage.setItem(KEY,JSON.stringify(pins));}catch(e){}}
 var first=aside.querySelector(".ess")||aside.querySelector("details.ngrp"),box=document.createElement("div");box.className="pinned";box.id="pinnedBox";aside.insertBefore(box,first);
 var cur=location.pathname;
 function draw(){
  box.innerHTML="";var any=0;
  pins.forEach(function(h){var src=aside.querySelector('details.ngrp a[href="'+h+'"]');if(!src)return;any++;
   if(any===1){var t=document.createElement("b");t.textContent="⭐ Pinned";box.appendChild(t);}
   var r=document.createElement("div");r.className="nrow";r.dataset.h=h;var a=document.createElement("a");a.href=h;a.textContent=src.textContent;if(src.classList.contains("on"))a.className="on";r.appendChild(a);
   var b=document.createElement("button");b.type="button";b.className="pin-btn on";b.title="Unpin";b.textContent="★";b.onclick=function(){toggle(h);};r.appendChild(b);box.appendChild(r);});
  box.style.display=any?"":"none";box.classList.toggle("canreorder",any>1);
  if(any>1)[].forEach.call(box.querySelectorAll(".nrow"),function(r){var g=document.createElement("span");g.className="pgrip";g.textContent="⠿";g.title="Drag to reorder your pins";r.insertBefore(g,r.firstChild);});
  aside.querySelectorAll("details.ngrp .nrow").forEach(function(r){var a=r.querySelector("a"),b=r.querySelector(".pin-btn"),h=a.getAttribute("href"),p=pins.indexOf(h)>-1;b.textContent=p?"★":"☆";b.classList.toggle("on",p);b.title=p?"Unpin":"Pin to top";});
 }
 box.addEventListener("pointerdown",function(e){var g=e.target.closest&&e.target.closest(".pgrip");if(!g||e.button!==0)return;var row=g.closest(".nrow");e.preventDefault();var id=e.pointerId,go=false;
  function mv(ev){if(ev.pointerId!==id)return;if(!go){go=true;row.classList.add("pdrag");}var hit=document.elementFromPoint(ev.clientX,ev.clientY),t=hit&&hit.closest&&hit.closest("#pinnedBox .nrow");
   if(t&&t!==row){var r=t.getBoundingClientRect();box.insertBefore(row,ev.clientY<r.top+r.height/2?t:t.nextSibling);}ev.preventDefault();}
  function up(ev){if(ev.pointerId!==id)return;document.removeEventListener("pointermove",mv);document.removeEventListener("pointerup",up);if(!go)return;row.classList.remove("pdrag");
   pins=[].map.call(box.querySelectorAll(".nrow"),function(r){return r.dataset.h;}).concat(pins.filter(function(h){return !aside.querySelector('#pinnedBox .nrow[data-h="'+h+'"]');}));save();draw();}
  document.addEventListener("pointermove",mv,{passive:false});document.addEventListener("pointerup",up);});
 function toggle(h){var i=pins.indexOf(h);if(i>-1)pins.splice(i,1);else pins.push(h);save();draw();}
 window.__pins=function(){return pins.slice();};window.__togglePin=toggle;
 aside.querySelectorAll("details.ngrp:not(.side-foot)>a").forEach(function(a){var r=document.createElement("div");r.className="nrow";a.parentNode.insertBefore(r,a);r.appendChild(a);var b=document.createElement("button");b.type="button";b.className="pin-btn";b.textContent="☆";b.setAttribute("aria-label","Pin this page");b.onclick=function(e){e.preventDefault();toggle(a.getAttribute("href"));};r.appendChild(b);});
 draw();
})();
