/* Site behaviour: menu, image viewer (a managed modal dialog), list filters with result counts,
   and remembering filtered results so detail pages can link back to them. No external libraries. */
(function () {
  "use strict";
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  /* ---- menu ---- */
  var t = document.querySelector(".navtoggle"), nav = document.getElementById("site-nav");
  if (t && nav) {
    t.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      t.setAttribute("aria-expanded", open ? "true" : "false");
      t.textContent = open ? "Close menu" : "Menu";
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && nav.classList.contains("open")) { nav.classList.remove("open"); t.setAttribute("aria-expanded", "false"); t.textContent = "Menu"; t.focus(); }
    });
  }

  /* ---- image viewer ---- */
  var links = $$("a.lb");
  if (links.length) {
    var box = document.createElement("div");
    box.className = "lbx";
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-modal", "true");
    box.setAttribute("aria-label", "Image viewer");
    box.innerHTML = '<div class="bar"><button class="zm" type="button" aria-pressed="false">Zoom in</button>' +
      '<a class="full btnlike" href="#" target="_blank" rel="noopener">Open full size</a>' +
      '<button class="x" type="button">Close</button></div>' +
      '<div class="stage"><img alt=""></div><div class="cap"></div>' +
      '<button class="pv" type="button" aria-label="Previous image">‹</button><button class="nx" type="button" aria-label="Next image">›</button>';
    document.body.appendChild(box);
    var stage = box.querySelector(".stage"), im = box.querySelector("img"), cap = box.querySelector(".cap");
    var zm = box.querySelector(".zm"), full = box.querySelector(".full");
    var idx = 0, lastFocus = null, hidden = [];
    function capFor(a) {
      if (a.dataset.cap) return document.createTextNode(a.dataset.cap).textContent.replace(/[<>&]/g, function (c) { return { "<": "&lt;", ">": "&gt;", "&": "&amp;" }[c]; });
      var fig = a.closest("figure"), fc = fig && fig.querySelector("figcaption");
      return fc ? fc.innerHTML : ((a.querySelector("img") || {}).alt || "");
    }
    function setZoom(on) { stage.classList.toggle("zoom", on); zm.setAttribute("aria-pressed", on ? "true" : "false"); zm.textContent = on ? "Fit to screen" : "Zoom in"; }
    function show(i) {
      idx = (i + links.length) % links.length;
      var a = links[idx];
      setZoom(false);
      im.src = a.getAttribute("href");
      im.alt = (a.querySelector("img") || {}).alt || "";
      full.href = a.getAttribute("href");
      cap.innerHTML = capFor(a) + (a.dataset.page ? ' <a href="' + a.dataset.page + '">Details and source</a>' : "");
      var many = links.length > 1;
      box.querySelector(".pv").hidden = !many; box.querySelector(".nx").hidden = !many;
    }
    function focusables() { return $$('button:not([hidden]), a[href]', box).filter(function (el) { return el.offsetParent !== null; }); }
    function open(i) {
      lastFocus = document.activeElement; show(i);
      box.classList.add("open"); document.body.style.overflow = "hidden";
      hidden = $$("body > *").filter(function (el) { return el !== box && !el.hasAttribute("inert"); });
      hidden.forEach(function (el) { el.setAttribute("inert", ""); el.setAttribute("aria-hidden", "true"); });
      box.querySelector(".x").focus();
    }
    function close() {
      box.classList.remove("open"); im.removeAttribute("src"); document.body.style.overflow = "";
      hidden.forEach(function (el) { el.removeAttribute("inert"); el.removeAttribute("aria-hidden"); });
      if (lastFocus) lastFocus.focus();
    }
    links.forEach(function (a, i) {
      a.addEventListener("click", function (e) { if (e.metaKey || e.ctrlKey || e.shiftKey) return; e.preventDefault(); open(i); });
    });
    box.querySelector(".x").addEventListener("click", close);
    zm.addEventListener("click", function () { setZoom(!stage.classList.contains("zoom")); });
    im.addEventListener("click", function () { setZoom(!stage.classList.contains("zoom")); });
    box.querySelector(".pv").addEventListener("click", function () { show(idx - 1); });
    box.querySelector(".nx").addEventListener("click", function () { show(idx + 1); });
    box.addEventListener("click", function (e) { if (e.target === box || e.target === stage) close(); });
    box.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { e.preventDefault(); close(); return; }
      if (e.key === "ArrowLeft" && !stage.classList.contains("zoom")) show(idx - 1);
      else if (e.key === "ArrowRight" && !stage.classList.contains("zoom")) show(idx + 1);
      else if (e.key === "Tab") {
        var f = focusables(); if (!f.length) return;
        var first = f[0], last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    });
  }

  /* ---- filters: an input[data-filter] hides [data-q] items that don't match; family chips narrow further ---- */
  function norm(s) { return (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/õ/g, "o"); }
  $$("input[data-filter]").forEach(function (inp) {
    var root = document.querySelector(inp.dataset.filter);
    if (!root) return;
    var items = $$("[data-q]", root), id = inp.id, noun = inp.dataset.noun || "items";
    var count = document.querySelector('[data-count="' + id + '"]'), none = document.querySelector('[data-none="' + id + '"]');
    var resets = $$('[data-reset="' + id + '"]'), chips = $$(".chips [data-fam]");
    var fam = "all";
    function apply(push) {
      var q = norm(inp.value.trim()), shown = 0;
      items.forEach(function (el) {
        var ok = (!q || norm(el.dataset.q).indexOf(q) >= 0) && (fam === "all" || el.dataset.fam === fam || !el.dataset.fam);
        el.hidden = !ok; if (ok) shown++;
      });
      $$("[data-group]", root).forEach(function (g) {
        var vis = g.querySelector("[data-q]:not([hidden])");
        g.hidden = !vis;
        var nl = document.querySelector('[data-navfor="' + g.id + '"]'); if (nl) nl.hidden = !vis;
      });
      var active = q || fam !== "all";
      if (count) count.textContent = active ? shown + " of " + items.length + " " + noun : "";
      if (none) none.hidden = shown > 0;
      resets.forEach(function (b) { if (b.classList.contains("reset")) b.hidden = !active; });
      if (push) {
        var u = new URL(location.href);
        if (q) u.searchParams.set("q", inp.value.trim()); else u.searchParams.delete("q");
        if (fam !== "all") u.searchParams.set("fam", fam); else u.searchParams.delete("fam");
        history.replaceState(null, "", u);
      }
      try { sessionStorage.setItem("lastList:" + location.pathname, location.href); } catch (e) {}
    }
    var timer;
    inp.addEventListener("input", function () { clearTimeout(timer); timer = setTimeout(function () { apply(true); }, 120); });
    resets.forEach(function (b) { b.addEventListener("click", function () { inp.value = ""; fam = "all"; chips.forEach(function (c) { c.setAttribute("aria-pressed", c.dataset.fam === "all" ? "true" : "false"); }); apply(true); inp.focus(); }); });
    chips.forEach(function (c) {
      c.addEventListener("click", function () {
        fam = c.dataset.fam; chips.forEach(function (o) { o.setAttribute("aria-pressed", o === c ? "true" : "false"); }); apply(true);
      });
    });
    var params = new URLSearchParams(location.search);
    if (params.get("q")) inp.value = params.get("q");
    if (params.get("fam")) { fam = params.get("fam"); chips.forEach(function (o) { o.setAttribute("aria-pressed", o.dataset.fam === fam ? "true" : "false"); }); }
    if (params.get("q") || params.get("fam")) apply(false);
    else { try { sessionStorage.setItem("lastList:" + location.pathname, location.href); } catch (e) {} }
  });

  /* ---- detail pages: "Back to your results" returns to the filtered list the reader came from ---- */
  $$("a.back-results").forEach(function (a) {
    try {
      var target = new URL(a.href, location.href).pathname, saved = sessionStorage.getItem("lastList:" + target);
      if (saved && document.referrer && new URL(document.referrer).pathname === target) { a.href = saved; a.hidden = false; }
    } catch (e) {}
  });
})();
