/* Interactive map of places in the Rodilitz and Zaslow story (Leaflet + OpenStreetMap tiles).
   Theodore's side (Rodilitz, Hausman) = brick-red circles, Doris's side (Zaslow, Saslow) = blue squares, both = dark diamonds. Solid lines join recorded places;
   dashed lines are approximate. The chosen view and place are kept in the URL (?view=…&place=…). If the
   background tiles fail, a notice appears and the place list, routes and printed maps still work. */
(function () {
  "use strict";
  var el = document.getElementById("map");
  var panel = document.getElementById("mappanel"), fail = document.getElementById("mapfail");
  var ROOT = (document.querySelector('link[href$="assets/site.css"]').getAttribute("href") || "").replace(/assets\/site\.css$/, "");
  if (!el || !window.L) { if (fail) fail.hidden = false; return; }
  var COL = { r: "#8A2B1E", z: "#1E3F6B", both: "#1C1B18" };
  var map = L.map(el, { scrollWheelZoom: false, worldCopyJump: true, zoomSnap: 0.25 });
  var tiles = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors', maxZoom: 18
  }).addTo(map);
  var errors = 0, loaded = 0;
  tiles.on("tileerror", function () { errors++; if (errors >= 4 && loaded === 0 && fail) fail.hidden = false; });
  tiles.on("tileload", function () { loaded++; if (fail) fail.hidden = true; });
  map.on("focus", function () { map.scrollWheelZoom.enable(); });
  map.on("blur", function () { map.scrollWheelZoom.disable(); });

  function esc(s) { return String(s || "").replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function icon(f, active) {
    var s = active ? 20 : 15, c = COL[f] || COL.both;
    var shape = f === "z" ? '<rect x="2" y="2" width="' + (s - 4) + '" height="' + (s - 4) + '" fill="' + c + '" stroke="#fff" stroke-width="2"/>'
      : f === "r" ? '<circle cx="' + s / 2 + '" cy="' + s / 2 + '" r="' + (s / 2 - 1.5) + '" fill="' + c + '" stroke="#fff" stroke-width="2"/>'
      : '<rect x="' + s * 0.2 + '" y="' + s * 0.2 + '" width="' + s * 0.6 + '" height="' + s * 0.6 + '" transform="rotate(45 ' + s / 2 + " " + s / 2 + ')" fill="' + c + '" stroke="#fff" stroke-width="2"/>';
    return L.divIcon({ className: "mk", html: '<svg width="' + s + '" height="' + s + '" viewBox="0 0 ' + s + " " + s + '" aria-hidden="true">' + shape + "</svg>", iconSize: [s, s], iconAnchor: [s / 2, s / 2] });
  }
  var famName = { r: "Theodore’s side · Rodilitz and Hausman", z: "Doris’s side · Zaslow and Saslow", both: "Both sides" };
  var listHTML = panel.innerHTML;

  fetch(ROOT + "assets/places.json").then(function (r) { return r.json(); }).then(function (D) {
    var markers = {}, lines = [], active = null, view = "homes";
    D.routes.forEach(function (r) {
      var pl = L.polyline(r.pts, { color: COL[r.fam] || COL.both, weight: 2.6, opacity: 0.9, dashArray: r.dashed ? "7 6" : null, interactive: !!r.label });
      if (r.label) pl.bindTooltip(esc(r.label), { sticky: true });
      lines.push({ r: r, pl: pl });
    });
    D.places.forEach(function (p) {
      var m = L.marker([p.lat, p.lon], { icon: icon(p.fam), title: p.name, alt: p.name, keyboard: true, riseOnHover: true }).addTo(map);
      m.bindTooltip(esc(p.name.replace(/ \(.*\)$/, "")), { direction: "right", offset: [9, 0], className: "plabel" });
      m.on("click", function () { show(p.id, true); });
      markers[p.id] = { m: m, p: p };
    });
    function setURL(place) {
      var u = new URL(location.href);
      u.searchParams.set("view", view);
      if (place) u.searchParams.set("place", place); else u.searchParams.delete("place");
      history.replaceState(null, "", u);
    }
    function show(id, push) {
      var o = markers[id]; if (!o) return;
      if (active && markers[active]) markers[active].m.setIcon(icon(markers[active].p.fam));
      active = id; o.m.setIcon(icon(o.p.fam, true));
      var p = o.p, h = [];
      h.push('<p class="small"><a href="?view=' + view + '" data-back="1">← All places</a></p>');
      h.push('<span class="kicker" style="color:' + COL[p.fam] + '">' + famName[p.fam] + "</span><h2>" + esc(p.name) + "</h2>");
      if (p.alt) h.push('<div class="small">' + esc(p.alt) + "</div>");
      h.push("<h3>What happened here</h3>");
      p.events.forEach(function (e) { h.push('<div class="ev"><b>' + esc(e.d) + "</b> · " + esc(e.t) + "</div>"); });
      if (p.people.length) h.push('<h3>People</h3><div class="people-chips">' + p.people.map(function (x) { return '<a class="pn ' + x.f + '" href="' + ROOT + x.u + '">' + esc(x.n) + "</a>"; }).join(" · ") + "</div>");
      p.photos.forEach(function (ph) { h.push('<a href="' + ROOT + ph.full + '"><img src="' + ROOT + ph.src + '" alt="' + esc(ph.alt) + '" loading="lazy"></a><div class="small">' + esc(ph.cap) + "</div>"); });
      if (p.chapter) h.push('<p class="small" style="margin-top:12px"><a href="' + ROOT + "history/" + p.chapter + '.html">Read about it in the history</a></p>');
      panel.innerHTML = h.join("");
      var back = panel.querySelector("[data-back]");
      back.addEventListener("click", function (e) { e.preventDefault(); resetPanel(); setURL(null); });
      if (push) setURL(id);
      var vb = D.views[view];
      if (vb && !L.latLngBounds(vb).contains(o.m.getLatLng())) map.setView(o.m.getLatLng(), Math.max(map.getZoom(), 6));
    }
    function wireList() {
      Array.prototype.forEach.call(panel.querySelectorAll("[data-p]"), function (a) {
        a.addEventListener("click", function (e) { e.preventDefault(); var o = markers[a.dataset.p]; map.setView(o.m.getLatLng(), Math.max(map.getZoom(), 7)); show(a.dataset.p, true); panel.focus && panel.scrollTo(0, 0); });
      });
    }
    function resetPanel() {
      if (active && markers[active]) markers[active].m.setIcon(icon(markers[active].p.fam));
      active = null; panel.innerHTML = listHTML; wireList();
    }
    var btns = document.querySelectorAll("[data-view]");
    function setView(v, keepPlace) {
      view = v;
      Array.prototype.forEach.call(btns, function (b) { b.setAttribute("aria-pressed", b.dataset.view === v ? "true" : "false"); });
      lines.forEach(function (o) {
        var on = v === "all" || o.r.views.indexOf(v) >= 0 || false;
        if (on && !map.hasLayer(o.pl)) o.pl.addTo(map);
        if (!on && map.hasLayer(o.pl)) map.removeLayer(o.pl);
      });
      var b = D.views[v];
      if (b) map.fitBounds(b, { padding: [10, 10] });
      else map.fitBounds(L.featureGroup(Object.keys(markers).map(function (k) { return markers[k].m; })).getBounds(), { padding: [20, 20] });
      setURL(keepPlace ? active : null);
    }
    Array.prototype.forEach.call(btns, function (b) { b.addEventListener("click", function () { setView(b.dataset.view, true); }); });
    var q = new URLSearchParams(location.search);
    wireList();
    setView(D.views.hasOwnProperty(q.get("view")) ? q.get("view") : "homes", false);
    if (q.get("place") && markers[q.get("place")]) show(q.get("place"), true);
  });
})();
