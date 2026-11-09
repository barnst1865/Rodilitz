/* Family tree explorer. Starts with a readable local view: the chosen person, their parents, their husband or wife
   (with that spouse's parents) and their children. Grandparents and great-grandparents are added on request rather
   than shrinking names to fit. Every card is a button; the URL hash records the person, so Back works. */
(function () {
  "use strict";
  var canvas = document.getElementById("tcanvas"), scroller = document.getElementById("tscroll");
  var sel = document.getElementById("tsel"), side = document.getElementById("tside");
  if (!canvas) return;
  var ROOT = (document.querySelector('link[href$="assets/site.css"]').getAttribute("href") || "").replace(/assets\/site\.css$/, "");
  var CW = 176, CH = 92, GX = 18, GY = 46, PAD = 24, UP = 1, DOWN = 1;
  var P = {}, focus = null, mid = 0, fmid = 0;

  function esc(s) { return String(s || "").replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  Array.prototype.forEach.call(document.querySelectorAll("[data-up]"), function (b) {
    b.addEventListener("click", function () {
      UP = +b.dataset.up; DOWN = UP > 1 ? 2 : 1;
      Array.prototype.forEach.call(document.querySelectorAll("[data-up]"), function (o) { o.setAttribute("aria-pressed", o === b ? "true" : "false"); });
      if (focus) draw(focus);
    });
  });
  var cbtn = document.getElementById("tcenter");
  if (cbtn) cbtn.addEventListener("click", center);

  fetch(ROOT + "assets/people.json").then(function (r) { return r.json(); }).then(function (data) {
    P = data;
    var ids = Object.keys(P).sort(function (a, b) {
      if (P[a].f !== P[b].f) return P[a].f < P[b].f ? 1 : -1;
      return P[a].n.localeCompare(P[b].n);
    });
    var groups = { r: "Theodore’s side: Rodilitz, Hausman and relatives", z: "Doris’s side: Zaslow, Saslow and relatives" };
    ["r", "z"].forEach(function (f) {
      var og = document.createElement("optgroup"); og.label = groups[f];
      ids.filter(function (i) { return P[i].f === f; }).forEach(function (i) {
        var o = document.createElement("option"); o.value = i; o.textContent = P[i].n + (P[i].d ? " (" + P[i].d + ")" : "");
        og.appendChild(o);
      });
      sel.appendChild(og);
    });
    sel.addEventListener("change", function () { go(sel.value); });
    window.addEventListener("hashchange", function () { var h = location.hash.slice(1); if (P[h] && h !== focus) draw(h); });
    var start = location.hash.slice(1);
    draw(P[start] ? start : (P["R-001"] ? "R-001" : ids[0]));
  }).catch(function () {
    canvas.innerHTML = '<p class="small" style="padding:16px">The interactive tree could not load. The list of all family lines below shows the same relationships.</p>';
  });

  function go(id) { if (location.hash.slice(1) !== id) location.hash = id; else draw(id); }

  function ancLayout(id, gen) {
    var par = (P[id].p || []).filter(function (x) { return P[x]; });
    if (gen >= UP || !par.length) return { w: CW, nodes: [{ id: id, x: 0, gen: gen }], cx: CW / 2 };
    var subs = par.map(function (x) { return ancLayout(x, gen + 1); });
    var w = 0, nodes = [], centers = [];
    subs.forEach(function (s, k) {
      if (k) w += GX;
      s.nodes.forEach(function (n) { nodes.push({ id: n.id, x: n.x + w, gen: n.gen }); });
      centers.push(w + s.cx); w += s.w;
    });
    var cx = (centers[0] + centers[centers.length - 1]) / 2;
    if (w < CW) { var d = (CW - w) / 2; nodes.forEach(function (n) { n.x += d; }); cx += d; w = CW; }
    nodes.push({ id: id, x: cx - CW / 2, gen: gen });
    return { w: w, nodes: nodes, cx: cx };
  }
  function kidsOf(id, spouse) {
    var c = (P[id].c || []).slice();
    if (spouse && P[spouse]) (P[spouse].c || []).forEach(function (k) { if (c.indexOf(k) < 0 && (P[k].p || []).indexOf(id) >= 0) c.push(k); });
    return c.filter(function (k) { return P[k]; });
  }
  function descLayout(id, depth, spouse) {
    var kids = depth < DOWN ? kidsOf(id, spouse) : [];
    if (!kids.length) return { w: CW, nodes: [], cx: CW / 2 };
    var w = 0, nodes = [], centers = [];
    kids.forEach(function (k, i) {
      var s = descLayout(k, depth + 1, null);
      if (i) w += GX;
      s.nodes.forEach(function (n) { nodes.push({ id: n.id, x: n.x + w, gen: n.gen }); });
      nodes.push({ id: k, x: w + s.cx - CW / 2, gen: -(depth + 1) });
      centers.push(w + s.cx); w += s.w;
    });
    var cx = (centers[0] + centers[centers.length - 1]) / 2;
    if (w < CW) { var d = (CW - w) / 2; nodes.forEach(function (n) { n.x += d; }); cx += d; w = CW; }
    return { w: w, nodes: nodes, cx: cx };
  }

  function center() {
    /* On a narrow screen, keep the selected person in view rather than the middle of the couple. */
    var c = scroller.clientWidth < 2 * CW + 4 * GX ? fmid : mid;
    scroller.scrollLeft = Math.max(0, c - scroller.clientWidth / 2);
  }

  function draw(id) {
    focus = id; sel.value = id;
    var p = P[id], spouse = (p.sp || []).filter(function (s) { return P[s]; })[0] || null;
    var A = ancLayout(id, 0), B = spouse ? ancLayout(spouse, 0) : null;
    var nodes = A.nodes.slice(), topW = A.w, fx = A.cx, sx = null;
    if (B) {
      var off = A.w + GX * 2;
      B.nodes.forEach(function (n) { nodes.push({ id: n.id, x: n.x + off, gen: n.gen, sp: true }); });
      sx = off + B.cx; topW = off + B.w;
    }
    var m = sx !== null ? (fx + sx) / 2 : fx;
    var D = descLayout(id, 0, spouse), dOff = m - D.cx;
    D.nodes.forEach(function (n) { nodes.push({ id: n.id, x: n.x + dOff, gen: n.gen }); });
    var minX = Math.min(0, dOff), maxX = Math.max(topW, dOff + D.w), maxGen = 0, minGen = 0;
    nodes.forEach(function (n) { maxGen = Math.max(maxGen, n.gen); minGen = Math.min(minGen, n.gen); });
    var W = Math.max(maxX - minX + PAD * 2, 320), Hh = (maxGen - minGen + 1) * (CH + GY) - GY + PAD * 2;
    function X(n) { return n.x - minX + PAD; }
    function Y(g) { return (maxGen - g) * (CH + GY) + PAD; }
    var byKey = {};
    nodes.forEach(function (n) { byKey[n.id + "@" + n.gen + (n.sp ? "s" : "")] = n; });
    var html = [], lines = [];
    nodes.forEach(function (n) {
      var q = P[n.id], cls = "tcard " + q.f + (n.id === id ? " focus" : "");
      if ((n.gen >= UP && (q.p || []).length) || (n.gen <= -DOWN && (q.c || []).length)) cls += " more";
      var sp = (n.gen < 0 && (q.sp || []).length && P[q.sp[0]]) ? "<br>= " + esc(P[q.sp[0]].s) : "";
      var link = n.id === id ? '<a class="lnk" href="' + ROOT + q.u + '">Open page</a>' : "";
      var label = q.n + (q.d ? ", " + q.d : "") + (n.id === id ? " (selected)" : "");
      html.push('<div class="' + cls + '" role="button" tabindex="0" aria-label="' + esc(label) + '" data-id="' + n.id + '" style="left:' + X(n) + "px;top:" + Y(n.gen) + 'px">' +
        '<span class="nm">' + esc(q.n) + "</span>" + esc(q.d) + sp + link + "</div>");
    });
    function line(x1, y1, x2, y2, dash) {
      var ym = y1 + (y2 - y1) / 2;
      lines.push('<path d="M' + x1 + "," + y1 + " V" + ym + " H" + x2 + " V" + y2 + '" fill="none" stroke="#3D4B5E" stroke-width="1.4"' + (dash ? ' stroke-dasharray="5 4"' : "") + "/>");
    }
    nodes.forEach(function (n) {
      var q = P[n.id];
      if (n.gen >= 0) {
        var par = (q.p || []).map(function (x) { return byKey[x + "@" + (n.gen + 1) + (n.sp ? "s" : "")]; }).filter(Boolean);
        if (!par.length) return;
        var cx = par.length > 1 ? (X(par[0]) + X(par[par.length - 1])) / 2 + CW / 2 : X(par[0]) + CW / 2;
        if (par.length > 1) lines.push('<line x1="' + (X(par[0]) + CW) + '" y1="' + (Y(n.gen + 1) + CH / 2) + '" x2="' + X(par[par.length - 1]) + '" y2="' + (Y(n.gen + 1) + CH / 2) + '" stroke="#3D4B5E" stroke-width="1.4"/>');
        line(cx, par.length > 1 ? Y(n.gen + 1) + CH / 2 : Y(n.gen + 1) + CH, X(n) + CW / 2, Y(n.gen), q.q);
      } else {
        var pg = n.gen + 1, parent = null;
        (q.p || []).forEach(function (x) { var c = byKey[x + "@" + pg]; if (c && !parent) parent = c; });
        if (!parent) return;
        var px = X(parent) + CW / 2, py = Y(pg) + CH;
        if (pg === 0 && sx !== null) { px = m - minX + PAD; py = Y(0) + CH / 2; }
        line(px, py, X(n) + CW / 2, Y(n.gen), q.q);
      }
    });
    if (sx !== null) {
      var y = Y(0) + CH / 2, x1 = fx - minX + PAD + CW / 2, x2 = sx - minX + PAD - CW / 2;
      lines.push('<line x1="' + x1 + '" y1="' + (y - 2) + '" x2="' + x2 + '" y2="' + (y - 2) + '" stroke="#0F172A" stroke-width="1.4"/>');
      lines.push('<line x1="' + x1 + '" y1="' + (y + 2) + '" x2="' + x2 + '" y2="' + (y + 2) + '" stroke="#0F172A" stroke-width="1.4"/>');
    }
    canvas.style.width = W + "px"; canvas.style.height = Hh + "px";
    canvas.innerHTML = '<svg class="lines" width="' + W + '" height="' + Hh + '" aria-hidden="true">' + lines.join("") + "</svg>" + html.join("");
    Array.prototype.forEach.call(canvas.querySelectorAll(".tcard"), function (el) {
      el.addEventListener("click", function (e) { if (e.target.tagName === "A") return; go(el.dataset.id); });
      el.addEventListener("keydown", function (e) { if ((e.key === "Enter" || e.key === " ") && e.target === el) { e.preventDefault(); go(el.dataset.id); } });
    });
    mid = m - minX + PAD; fmid = fx - minX + PAD; center();

    function list(title, arr) {
      arr = arr.filter(function (x) { return P[x]; });
      if (!arr.length) return "";
      return "<div><h3>" + title + "</h3><ul>" + arr.map(function (x) {
        return '<li><a class="pn ' + P[x].f + '" href="#' + x + '">' + esc(P[x].n) + "</a>" + (P[x].d ? ' <span class="d">' + esc(P[x].d) + "</span>" : "") + "</li>";
      }).join("") + "</ul></div>";
    }
    var sibs = [];
    (p.p || []).forEach(function (x) { if (P[x]) (P[x].c || []).forEach(function (c) { if (c !== id && sibs.indexOf(c) < 0) sibs.push(c); }); });
    side.innerHTML = '<div><h3>Selected</h3><p><a class="pn ' + p.f + '" href="' + ROOT + p.u + '">' + esc(p.n) + "</a>" + (p.d ? ' <span class="d">' + esc(p.d) + "</span>" : "") +
      '<br><a href="' + ROOT + p.u + '">Biography, records and photographs</a></p></div>' + list("Brothers and sisters", sibs) + list("Other marriages", (p.sp || []).slice(1));
  }
})();
