// tracking.js — Monte-Cristo Patrimoine
// GA4 events : booking_open · cta_click · contact_click
(function () {
  function track(event, params) {
    if (typeof gtag !== 'function') return;
    gtag('event', event, params);
  }

  var page = window.location.pathname;

  // 1. booking_open — clic sur le calendrier Microsoft Bookings (conversion principale)
  var facade = document.getElementById('booking-facade');
  if (facade) {
    facade.addEventListener('click', function () {
      track('booking_open', { page_path: page });
    });
  }

  // 2. cta_click — tout bouton qui mène vers la section contact
  document.querySelectorAll('a[href="/#contact"], a[href="#contact"]').forEach(function (el) {
    el.addEventListener('click', function () {
      track('cta_click', {
        page_path: page,
        cta_label: el.textContent.trim().slice(0, 50)
      });
    });
  });

  // 3. contact_click — téléphone et email (conversions alternatives)
  document.querySelectorAll('a[href^="tel:"], a[href^="mailto:"]').forEach(function (el) {
    el.addEventListener('click', function () {
      track('contact_click', {
        contact_type: el.href.startsWith('tel:') ? 'phone' : 'email',
        page_path: page
      });
    });
  });
})();
