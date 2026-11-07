// ---------- passwords: 👁 show/hide on every password box, plus a live rules checklist + strength bar on "new password" boxes ----------
(function(){
 function rules(v){return [["8 or more characters",v.length>=8],["An UPPERCASE letter",/[A-Z]/.test(v)],["A special character (! @ # $ %)",/[^A-Za-z0-9]/.test(v)],["Not a common word or sequence",v.length>0&&!/password|qwerty|123456|letmein|iloveyou/i.test(v)&&!/(.)\1{3,}/.test(v)]];}
 function score(v){var r=rules(v).filter(function(x){return x[1];}).length,b=0;if(v.length>=12)b++;if(/[a-z]/.test(v)&&/[0-9]/.test(v))b++;return Math.min(4,Math.max(0,r-1+(r===4?b:0)));}
 document.querySelectorAll('input[type=password]').forEach(function(inp){
  var w=document.createElement('span');w.className='pwwrap';inp.parentNode.insertBefore(w,inp);w.appendChild(inp);
  var b=document.createElement('button');b.type='button';b.className='pweye';b.setAttribute('aria-label','Show password');b.title='Show / hide password';b.textContent='👁';
  b.onclick=function(){var s=inp.type==='password';inp.type=s?'text':'password';b.textContent=s?'🙈':'👁';b.setAttribute('aria-label',s?'Hide password':'Show password');};
  w.appendChild(b);
  if(inp.hasAttribute('data-new')){
   var box=document.createElement('div');box.className='pwpol';box.innerHTML='<div class="pwbar"><i></i></div><div class="pwlbl muted"></div><ul></ul>';
   w.parentNode.insertBefore(box,w.nextSibling);
   var bar=box.querySelector('.pwbar i'),lbl=box.querySelector('.pwlbl'),ul=box.querySelector('ul');
   function upd(){var v=inp.value,s=score(v),names=['Too weak','Weak','Okay','Good','Strong'],cols=['#d64545','#e8590c','#e0a100','#5aa83c','#16a34a'];
    bar.style.width=(v?(s+1)*20:0)+'%';bar.style.background=cols[s];lbl.textContent=v?names[s]:'Choose a strong password';
    ul.innerHTML=rules(v).map(function(r){return '<li class="'+(r[1]?'ok':'')+'">'+r[0]+'</li>';}).join('');}
   inp.addEventListener('input',upd);upd();
  }
 });
})();
