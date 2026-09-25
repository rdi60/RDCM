(function () {
  const C = window.SITE_CONTENT;

  function el(tag, className, html) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (html !== undefined) node.innerHTML = html;
    return node;
  }

  function renderHero() {
    document.getElementById('hero-eyebrow').textContent = C.hero.eyebrow;
    document.getElementById('hero-headline').innerHTML =
      escapeHtml(C.hero.headlinePlain) +
      '<span class="grad-text">' + escapeHtml(C.hero.headlineAccent) + '</span>' +
      escapeHtml(C.hero.headlineEnd);
    document.getElementById('hero-role').textContent =
      C.doctor.name + ' — ' + C.doctor.credentials;

    const frame = document.getElementById('hero-photo-frame');
    if (C.photos.doctorPortrait) {
      frame.innerHTML = '<img class="hero-photo" src="' + C.photos.doctorPortrait + '" alt="' + escapeHtml(C.doctor.name) + '">';
    } else {
      frame.innerHTML =
        '<div class="hero-photo hero-photo-placeholder">' +
        '<span>Add a portrait photo — save it as <code>images/doctor-portrait.jpg</code> and set it in <code>data/content.js</code> (see CONTENT-GUIDE.md)</span>' +
        '</div>';
    }
  }

  function escapeHtml(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

  function renderProfile() {
    document.getElementById('profile-bio').textContent = C.hero.bio;

    const statRow = document.getElementById('profile-stats');
    C.highlights.forEach((h) => {
      const item = el('div', 'stat-item');
      item.appendChild(el('span', 'stat-value', escapeHtml(h.value)));
      item.appendChild(el('span', 'stat-label', escapeHtml(h.label)));
      statRow.appendChild(item);
    });

    document.getElementById('hospital-name').textContent = C.hospital.name;
    document.getElementById('hospital-location').textContent = C.hospital.location;
    document.getElementById('hospital-description').textContent = C.hospital.description;
    const img = document.getElementById('hospital-photo');
    img.src = C.hospital.photo;
    img.alt = C.hospital.name + ', ' + C.hospital.location;
  }

  function renderPublicationList(containerId, entries) {
    const list = document.getElementById(containerId);
    entries.forEach((pub) => {
      const li = el('li', 'list-row');
      li.appendChild(el('span', 'list-authors', escapeHtml(pub.authors)));
      li.appendChild(el('span', 'list-title', '“' + escapeHtml(pub.title) + '”'));
      li.appendChild(el('span', 'list-source', escapeHtml(pub.source)));
      list.appendChild(li);
    });
  }

  function renderEventList(containerId, entries) {
    const list = document.getElementById(containerId);
    entries.forEach((ev) => {
      const li = el('li', 'list-row');
      li.appendChild(el('span', 'list-title', escapeHtml(ev.event)));
      li.appendChild(el('span', 'list-authors', escapeHtml(ev.topic)));
      li.appendChild(el('span', 'list-source', escapeHtml(ev.place) + ' · ' + escapeHtml(ev.date)));
      list.appendChild(li);
    });
  }

  function renderRoleList(containerId, entries) {
    const list = document.getElementById(containerId);
    entries.forEach((r) => {
      const li = el('li', 'role-item');
      li.appendChild(el('span', 'role-title', escapeHtml(r.role || r.title)));
      if (r.org) li.appendChild(el('span', 'role-org', escapeHtml(r.org)));
      if (r.period) li.appendChild(el('span', 'role-period', escapeHtml(r.period)));
      list.appendChild(li);
    });
  }

  function renderAwards() {
    const highlights = document.getElementById('award-recognitions');
    C.awards.recognitions.forEach((rec) => {
      const card = el('div', 'award-card');
      card.appendChild(el('span', 'award-title', escapeHtml(rec.title)));
      card.appendChild(el('span', 'award-period', escapeHtml(rec.period)));
      highlights.appendChild(card);
    });
    renderRoleList('award-positions', C.awards.positions);
    renderRoleList('award-examinerships', C.awards.examinerships);
    renderRoleList('award-teaching', C.awards.teaching);
  }

  function renderContact() {
    const btn = document.getElementById('contact-email-btn');
    btn.href = 'mailto:' + C.contact.email;
    btn.textContent = C.contact.email;

    const note = document.getElementById('contact-note');
    const parts = [];
    if (C.contact.address) parts.push(C.contact.address);
    if (C.contact.phone) parts.push(C.contact.phone);
    note.textContent = parts.length
      ? parts.join(' · ')
      : 'Clinic address and phone number will be added here soon.';
  }

  function renderFooter() {
    document.getElementById('footer-name').textContent = C.doctor.name;
    document.getElementById('year').textContent = new Date().getFullYear();
  }

  function setupTabs() {
    document.querySelectorAll('.tabs').forEach((tabGroup) => {
      const buttons = tabGroup.querySelectorAll('.tab-btn');
      buttons.forEach((btn) => {
        btn.addEventListener('click', () => {
          buttons.forEach((b) => {
            b.classList.toggle('active', b === btn);
            b.setAttribute('aria-selected', b === btn ? 'true' : 'false');
            const panel = document.getElementById(b.getAttribute('data-tab'));
            if (panel) panel.hidden = b !== btn;
          });
        });
      });
    });
  }

  function setupNav() {
    const navToggle = document.getElementById('nav-toggle');
    const navLinks = document.getElementById('nav-links');
    navToggle.addEventListener('click', () => {
      const isOpen = navLinks.classList.toggle('open');
      navToggle.setAttribute('aria-expanded', String(isOpen));
    });
    navLinks.querySelectorAll('a').forEach((link) => {
      link.addEventListener('click', () => {
        navLinks.classList.remove('open');
        navToggle.setAttribute('aria-expanded', 'false');
      });
    });
  }

  function setupReveal() {
    const revealEls = document.querySelectorAll('.reveal');
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12 }
    );
    revealEls.forEach((elm) => observer.observe(elm));
  }

  document.addEventListener('DOMContentLoaded', () => {
    renderHero();
    renderProfile();
    renderPublicationList('pub-international', C.publications.international);
    renderPublicationList('pub-national', C.publications.national);
    renderEventList('conf-international', C.conferences.internationalInvited);
    renderEventList('conf-national', C.conferences.nationalInvited);
    renderEventList('conf-workshops', C.conferences.workshopsOrganized);
    renderAwards();
    renderContact();
    renderFooter();

    setupTabs();
    setupNav();
    setupReveal();
  });
})();
