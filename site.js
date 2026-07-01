// ── Hamburger menu ──────────────────────────────────────────────────────────
var hamburger=document.querySelector('.hamburger');
if(hamburger){
  hamburger.addEventListener('click',function(){
    var nav=this.closest('header').querySelector('.nav');
    nav.classList.toggle('open');
    this.setAttribute('aria-expanded',nav.classList.contains('open'));
  });
}

// ── Booking iframe (index.html) ──────────────────────────────────────────────
var bookingFacade=document.getElementById('booking-facade');
if(bookingFacade){
  bookingFacade.addEventListener('click',function(){
    var facade=document.getElementById('booking-facade');
    var iframe=document.getElementById('booking-iframe');
    iframe.src='https://outlook.office.com/book/Prisederendezvous@montecristopatrimoine.onmicrosoft.com/?ismsaljsauthenabled';
    facade.style.display='none';
    iframe.style.display='block';
    iframe.scrollIntoView({behavior:'smooth',block:'start'});
  });
}

// ── Blog filter (blog.html) ──────────────────────────────────────────────────
(function(){
  var chips=document.querySelectorAll('.filter-chip');
  var cards=document.querySelectorAll('.article-card');
  var countEl=document.getElementById('visible-count');
  var filterActiveEl=document.getElementById('filter-active');
  var emptyEl=document.getElementById('empty');
  var gridEl=document.getElementById('grid');
  if(!chips.length||!cards.length)return;

  function applyFilter(filter){
    var visible=0;
    cards.forEach(function(card){
      var matches=filter==='all'||card.dataset.topic===filter;
      card.classList.toggle('hidden',!matches);
      if(matches)visible++;
    });
    countEl.textContent=visible;
    var label=filter==='all'?'':'— '+document.querySelector('.filter-chip[data-filter="'+filter+'"]').textContent;
    filterActiveEl.textContent=label;
    gridEl.style.display=visible===0?'none':'';
    emptyEl.classList.toggle('show',visible===0);
  }

  chips.forEach(function(chip){
    chip.addEventListener('click',function(){
      chips.forEach(function(c){c.classList.remove('active');});
      chip.classList.add('active');
      applyFilter(chip.dataset.filter);
    });
  });
})();
