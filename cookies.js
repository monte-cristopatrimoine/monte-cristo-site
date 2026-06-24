(function(){

if(localStorage.getItem('mcp_cookies')!==null)return;

var style=document.createElement('style');
style.textContent=`
#mcp-cookie-banner{
position: fixed;
bottom: 24px;
left: 50%;
transform: translateX(-50%);
z-index: 9999;
width: calc(100%-48px);
max-width: 680px;
background: #16110A;
color: #FDFAF3;
border-radius: 16px;
padding: 20px 24px;
box-shadow: 0 8px 40px rgba(0,0,0,0.22);
display: flex;
align-items: center;
justify-content: space-between;
gap: 20px;
font-family: Arial,sans-serif;
font-size: 14px;
line-height: 1.5;
animation: mcp-slide-up 0.35s ease;
}
@keyframes mcp-slide-up{
from{opacity: 0;transform: translateX(-50%)translateY(20px);}
to{opacity: 1;transform: translateX(-50%)translateY(0);}
}
#mcp-cookie-banner p{
margin: 0;
opacity: 0.85;
flex: 1;
}
#mcp-cookie-banner a{
color: #FDFAF3;
opacity: 1;
}
#mcp-cookie-banner .mcp-cookie-btns{
display: flex;
gap: 10px;
flex-shrink: 0;
}
#mcp-cookie-banner button{
font-family: Arial,sans-serif;
font-size: 13px;
font-weight: 600;
border-radius: 999px;
padding: 9px 20px;
border: none;
cursor: pointer;
transition: opacity 0.15s;
white-space: nowrap;
}
#mcp-cookie-banner button:hover{opacity: 0.85;}
#mcp-cookie-btn-accept{
background: #346848;
color: #FDFAF3;
}
#mcp-cookie-btn-refuse{
background: transparent;
color: #FDFAF3;
border: 1px solid rgba(253,250,243,0.35)!important;
}
@media(max-width: 600px){
#mcp-cookie-banner{
flex-direction: column;
align-items: flex-start;
bottom: 0;
left: 0;
right: 0;
transform: none;
width: 100%;
max-width: 100%;
border-radius: 16px 16px 0 0;
}
#mcp-cookie-banner .mcp-cookie-btns{
width: 100%;
}
#mcp-cookie-banner button{
flex: 1;
text-align: center;
}
}
`;
document.head.appendChild(style);

var banner=document.createElement('div');
banner.id='mcp-cookie-banner';
banner.innerHTML=`
<p>Nous utilisons des cookies de mesure d'audience(Google Analytics)pour améliorer notre site.
<a href="/mentions-legales#article-8">En savoir plus</a></p>
<div class="mcp-cookie-btns">
<button id="mcp-cookie-btn-refuse">Refuser</button>
<button id="mcp-cookie-btn-accept">Accepter</button>
</div>
`;
document.body.appendChild(banner);

function dismiss(choice){
localStorage.setItem('mcp_cookies',choice);

var exp=new Date();
exp.setMonth(exp.getMonth()+13);
document.cookie='mcp_cookies='+choice+';expires='+exp.toUTCString()+';path=/;SameSite=Lax';
banner.style.animation='none';
banner.style.opacity='0';
banner.style.transition='opacity 0.3s';
setTimeout(function(){banner.remove();},300);

if(choice==='accepted' && typeof gtag==='function'){
gtag('consent','update',{
analytics_storage: 'granted'
});
}
}
document.getElementById('mcp-cookie-btn-accept').addEventListener('click',function(){
dismiss('accepted');
});
document.getElementById('mcp-cookie-btn-refuse').addEventListener('click',function(){
dismiss('refused');
});
})();