(function () {
  const { html, render, useState, useMemo, useRef, useEffect } = htmPreact;
  const D = JSON.parse(document.getElementById("payload").textContent);
  const pct = (x) => (x == null ? "—" : (100 * x).toFixed(1) + "%");
  const f3 = (x) => (x == null ? "—" : x.toFixed(3));

  const SVGNS = "http://www.w3.org/2000/svg";
  const GRUPO = { abertura: "--abertura", conclusao: "--conclusao", tramitacao: "--tramitacao",
    assinatura: "--assinatura", criacao: "--criacao", comunicacao: "--comunicacao", blocos: "--blocos",
    edicao: "--edicao", automatico: "--automatico", outros: "--outros" };
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim() || "#B0B7C3";
  const COL_W = 120, LANE_H = 84, MARGIN_L = 170, MARGIN_T = 54, NODE_GAP = 40, MARGIN_R = 60;
  const el = (tag, attrs) => { const e = document.createElementNS(SVGNS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]); return e; };
  function shortLabel(t) {
    if (!t) return "";
    const toks = t.split("-").filter((x) => x !== "PROCESSO" && x !== "UNIDADE");
    const s = toks.join("-") || t;
    return s.length <= 16 ? s : toks.map((x) => x.slice(0, 4)).join("-");
  }
  function drawSwimlane(svg, c) {
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    const group = el("g", {}); svg.appendChild(group);
    if (!c.nodes || !c.nodes.length) {
      const t = el("text", { x: 20, y: 30, fill: "#888" }); t.textContent = "(vazio)";
      group.appendChild(t); return { group, W: 200, H: 120 };
    }
    const laneOrder = {}; c.lanes.forEach((l) => (laneOrder[l.unidade] = l.order));
    const maxX = c.max_x ?? Math.max(...c.nodes.map((n) => n.x));
    const colX = (x) => MARGIN_L + x * COL_W, laneY = (o) => MARGIN_T + o * LANE_H;
    const cells = {}, pos = {};
    c.nodes.forEach((n) => { (cells[n.lane + "|" + n.x] = cells[n.lane + "|" + n.x] || []).push(n); });
    Object.values(cells).forEach((g) => {
      g.sort((a, b) => (b.coverage || 0) - (a.coverage || 0));
      g.forEach((n, i) => {
        const off = g.length > 1 ? (i - (g.length - 1) / 2) * NODE_GAP : 0;
        pos[n.id] = { x: colX(n.x) + off, y: laneY(laneOrder[n.lane] ?? 0) };
      });
    });
    const fullTop = MARGIN_T - LANE_H * 0.58, fullBot = laneY(c.lanes.length - 1) + LANE_H * 0.58, fullH = fullBot - fullTop;
    [["INÍCIO", -0.6, 0.6, "#eaf4ee"], ["MEIO", 0.6, maxX - 0.6, "#f5f7fb"], ["FIM", maxX - 0.6, maxX + 0.6, "#fbeced"]]
      .forEach(([lab, a, b, col]) => {
        if (b <= a) return;
        group.appendChild(el("rect", { x: colX(a), y: fullTop, width: colX(b) - colX(a), height: fullH, fill: col, class: "phase-band" }));
        const t = el("text", { x: (colX(a) + colX(b)) / 2, y: fullTop + 13, "text-anchor": "middle", class: "phase-label" });
        t.textContent = lab; group.appendChild(t);
      });
    c.lanes.forEach((l) => {
      const y = laneY(l.order), xs = l.x_start ?? 0, xe = l.x_end ?? maxX;
      group.appendChild(el("rect", { x: colX(xs) - COL_W * 0.42, y: y - LANE_H * 0.42,
        width: colX(xe) - colX(xs) + COL_W * 0.84, height: LANE_H * 0.84, rx: 10,
        fill: l.order % 2 ? "#dee7f3" : "#ecf1f8", class: "lane-band" }));
      const t = el("text", { x: MARGIN_L - COL_W * 0.55, y: y + 4, "text-anchor": "end", class: "lane-label" });
      t.textContent = (l.unidade || "").split("/").slice(-2).join("/"); group.appendChild(t);
    });
    const labOf = {}; c.nodes.forEach((n) => (labOf[n.id] = n.label));
    const isRem = (t) => t && t.indexOf("PROCESSO-REMETIDO") === 0;
    const isRec = (t) => t && t.indexOf("PROCESSO-RECEBIDO") === 0;
    c.edges.forEach((e) => {
      const a = pos[e.from], b = pos[e.to]; if (!a || !b) return;
      const handoff = e.kind === "handoff" || isRem(labOf[e.from]) || isRec(labOf[e.to]); let d;
      if (handoff) { const mx = (a.x + b.x) / 2; d = `M${a.x},${a.y} C ${mx},${a.y} ${mx},${b.y} ${b.x},${b.y}`; }
      else d = `M${a.x},${a.y} L ${b.x},${b.y}`;
      group.appendChild(el("path", { d, class: "edge " + (e.on_spine ? "spine" : "norm") + (e.back_edge ? " back" : ""),
        "marker-end": e.on_spine ? "url(#as)" : "url(#an)" }));
    });
    c.nodes.forEach((n) => {
      const p = pos[n.id], r = 11 + 7 * (n.coverage || 0);
      const g = el("g", { class: "node" + (n.on_spine ? " spine" : ""), transform: `translate(${p.x},${p.y})` });
      g.appendChild(el("circle", { r, fill: css(GRUPO[n.grupo] || "--outros") }));
      if (n.is_start) g.appendChild(el("circle", { r: r + 5, class: "ring start" }));
      if (n.is_end) g.appendChild(el("circle", { r: r + 5, class: "ring end" }));
      const t = el("text", { x: 0, y: -r - 5, "text-anchor": "middle", transform: `rotate(-20 0 ${-r - 5})` });
      t.textContent = shortLabel(n.label); g.appendChild(t);
      const ti = el("title", {}); ti.textContent = `${n.label} · ${n.lane}`; g.appendChild(ti);
      group.appendChild(g);
    });
    const defs = el("defs", {});
    [["as", "#16314e"], ["an", "#c2cad6"]].forEach(([id, col]) => {
      const m = el("marker", { id, viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto-start-reverse" });
      m.appendChild(el("path", { d: "M0,0 L10,5 L0,10 z", fill: col })); defs.appendChild(m);
    });
    svg.insertBefore(defs, svg.firstChild);
    return { group, W: colX(maxX) + MARGIN_R, H: laneY(c.lanes.length - 1) + LANE_H * 0.85 };
  }

  function sequenceSwimlane(seq) {
    const states = seq.map((i) => D.states[i]);
    const grupos = seq.map((i) => (D.grupos || [])[i] || "outros");
    const split = (s) => { const k = s.indexOf("@"); const tipo = k < 0 ? s : s.slice(0, k);
      return [tipo, (k < 0 ? "" : s.slice(k + 1)) || "?"]; };
    const laneFirst = {}, laneX = {};
    states.forEach((s, i) => { const l = split(s)[1]; if (laneFirst[l] === undefined) laneFirst[l] = i;
      (laneX[l] = laneX[l] || []).push(i); });
    const lanesSorted = Object.keys(laneFirst).sort((a, b) => laneFirst[a] - laneFirst[b]);
    const order = {}; lanesSorted.forEach((l, i) => (order[l] = i));
    const n = states.length;
    const nodes = states.map((s, i) => { const [tipo, lane] = split(s);
      return { id: "s" + i, label: tipo, lane, x: i, grupo: grupos[i], coverage: 1,
        is_start: i === 0, is_end: i === n - 1,
        phase: i === 0 ? "start" : i === n - 1 ? "end" : "middle", on_spine: true }; });
    const edges = []; for (let i = 0; i < n - 1; i++) { const a = nodes[i], b = nodes[i + 1];
      edges.push({ from: a.id, to: b.id, kind: a.lane === b.lane ? "within" : "handoff", on_spine: true, back_edge: false }); }
    const lanes = lanesSorted.map((l) => ({ unidade: l, order: order[l],
      x_start: Math.min(...laneX[l]), x_end: Math.max(...laneX[l]) }));
    return { lanes, nodes, edges, max_x: Math.max(0, n - 1) };
  }

  function Glossary({ keys }) {
    const g = D.glossary || {};
    const items = keys.filter((k) => g[k]);
    if (!items.length) return null;
    return html`<details class="gloss"><summary>o que significam estes indicadores?</summary>
      <dl>${items.map((k) => html`<div><dt>${g[k].label}</dt>
        <dd>${g[k].long}</dd></div>`)}</dl></details>`;
  }

  function Stat({ v, label, title }) {
    return html`<div class="stat" title=${title || ""}><b>${v}</b><span>${label}</span></div>`;
  }

  function ModelTable({ models }) {
    if (!models) return html`<p class="muted">Sem modelos de processo típico —
      cluster com menos de 30 traces (não avaliado).</p>`;
    const names = Object.keys(models);
    const best = names.reduce((a, b) =>
      (models[b].top1 ?? 0) > (models[a].top1 ?? 0) ? b : a, names[0]);
    return html`<div>
      <table><thead><tr><th>modelo</th><th>top-1</th><th>top-3</th>
        <th>suffix DL↓</th><th>validity</th></tr></thead>
        <tbody>${names.map((n) => html`<tr class=${n === best ? "best" : ""}>
          <td>${n}</td><td>${pct(models[n].top1)}</td><td>${pct(models[n].top3)}</td>
          <td>${f3(models[n].suffix_dl)}</td><td>${pct(models[n].validity)}</td></tr>`)}
        </tbody></table>
      <${Glossary} keys=${["top1", "top3", "suffix_dl", "validity", "log_fitness"]} /></div>`;
  }

  function ClusterDetail({ c }) {
    if (!c) return html`<div class="panel empty">Selecione um cluster à esquerda.</div>`;
    const ev = c.eval;
    const maxT = Math.max(1, ...(c.tipos || []).map((t) => t.n));
    return html`<div class="panel">
      <div class="bigname">${c.nome}</div>
      <div class="muted">cluster <code>${c.label}</code> · rank #${c.rank}
        ${c.micro ? html` · ${c.micro} micro-clusters` : ""}</div>
      ${c.descricao && html`<p class="muted" style="margin-top:8px">${c.descricao}</p>`}
      ${c.marcadores?.length ? html`<div class="chips">
        ${c.marcadores.map((m) => html`<span class="chip">${m}</span>`)}</div>` : null}
      ${c.top_keywords?.length ? html`<div style="margin-top:10px">
        <div class="muted" style="margin-bottom:4px">palavras-chave da categoria</div>
        <div class="chips">${c.top_keywords.map((k) =>
          html`<span class="chip">${k.k} <b>${k.n}</b></span>`)}</div></div>` : null}
      ${c.sample_keywords?.length ? html`<div class="muted" style="margin-top:10px">
        exemplos de processos${c.n_members ? html` (3 de ${c.n_members.toLocaleString()})` : ""}:
        ${c.sample_keywords.map((s) => html`<div style="margin:3px 0 0 8px">
          <code>${s.pf}</code>${s.kw?.length ? html` — ${s.kw.join(" · ")}` : ""}</div>`)}</div>`
        : c.sample_protocolos?.length ? html`<div class="muted" style="margin-top:10px">
        exemplos: ${c.sample_protocolos.map((p) => html`<code style="margin-right:8px">${p}</code>`)}</div>` : null}
      <div class="kv">
        <div><div class="b">${(c.n ?? 0).toLocaleString()}</div><small>processos</small></div>
        ${c.concl != null ? html`<div><div class="b">${pct(c.concl / c.n)}</div><small>concluídos</small></div>` : null}
        <div><div class="b">${ev ? ev.n_traces.toLocaleString() : "—"}</div><small>traces avaliados</small></div>
        <div><div class="b">${ev ? ev.n_test : "—"}</div><small>test traces</small></div>
      </div>
      ${(c.tipos || []).length ? html`<div>
        <div class="muted" style="margin-bottom:4px">tipo_procedimento (top 3)</div>
        ${c.tipos.map((t) => html`<div class="mbar">
          <span class="mname" title=${t.tipo}>${t.tipo.slice(0, 18)}</span>
          <div class="track"><div class="fill" style=${`width:${(t.n / maxT) * 100}%;background:var(--warn)`}></div></div>
          <span class="val">${t.n}</span></div>`)}</div>` : null}
      <h3 style="margin:16px 0 6px;font-size:14px">Avaliação dos modelos
        ${ev?.log_fitness != null ? html`<span class="muted">· log-fitness ${f3(ev.log_fitness)}</span>` : ""}</h3>
      ${ev && ev.n_test < 15 ? html`<div class="note">⚠ Apenas ${ev.n_test} test traces —
        diferenças entre modelos aqui estão dentro do ruído amostral.</div>` : null}
      <${ModelTable} models=${ev?.models} />
      <${Timelines} c=${c} />
    </div>`;
  }

  function ClustersPanel() {
    const [ci, setCi] = useState(0);
    const combo = D.combos[ci];
    const [sel, setSel] = useState(combo.clusters[0]?.id);
    const [q, setQ] = useState("");
    const [sort, setSort] = useState("n");
    const list = useMemo(() => {
      const ql = q.trim().toLowerCase();
      const r = combo.clusters.filter((c) => !ql ||
        c.nome.toLowerCase().includes(ql) || c.label.includes(ql) ||
        (c.tipos || []).some((t) => t.tipo.toLowerCase().includes(ql)));
      const key = { n: (c) => -c.n, name: (c) => c.nome.toLowerCase(),
        top1: (c) => -((c.eval?.models?.gru?.top1) ?? (c.eval?.models?.markov?.top1) ?? -1),
        traces: (c) => -(c.eval?.n_traces ?? -1) }[sort];
      return [...r].sort((a, b) => { const ka = key(a), kb = key(b);
        return ka < kb ? -1 : ka > kb ? 1 : 0; });
    }, [q, sort, ci]);
    const cur = combo.clusters.find((c) => c.id === sel) || combo.clusters[0];
    const pickCombo = (i) => { setCi(i); setSel(D.combos[i].clusters[0]?.id); };
    return html`<div>
      <div class="togglebar">
        ${D.combos.map((cb, i) => html`<button class=${i === ci ? "on" : ""}
          onClick=${() => pickCombo(i)}>${cb.arm} · ${cb.algo}</button>`)}
      </div>
      <div class="split">
        <div class="panel">
          <input class="search" placeholder="buscar nome / tipo / id…"
            value=${q} onInput=${(e) => setQ(e.target.value)} />
          <div class="sortbtns">
            ${[["n", "tamanho"], ["name", "nome"], ["top1", "acurácia"], ["traces", "traces"]]
              .map(([k, lbl]) => html`<button class=${sort === k ? "on" : ""}
                onClick=${() => setSort(k)}>${lbl}</button>`)}
          </div>
          <ul class="clist">${list.map((c) => html`
            <li class=${"crow" + (c.id === sel ? " on" : "")} onClick=${() => setSel(c.id)}>
              <span class="cn">${c.nome}</span>
              <span class="cs">${(c.eval?.n_traces ?? c.n).toLocaleString()}${c.eval ? " · " + pct(
                c.eval.models?.gru?.top1 ?? c.eval.models?.markov?.top1) : ""}</span>
            </li>`)}
            ${!list.length && html`<li class="muted" style="padding:12px">nenhum cluster</li>`}
          </ul>
          <div class="muted" style="margin-top:8px">${list.length} de ${combo.clusters.length} clusters</div>
        </div>
        <${ClusterDetail} c=${cur} />
      </div></div>`;
  }

  const GROUPS = [
    ["observado", "Observado (não é modelo)"],
    ["classico", "Modelo clássico (treinado por contagem, CPU)"],
    ["neural", "Modelo neural (treinado por gradiente, GPU)"],
  ];

  function Swimlane({ t }) {
    const ref = useRef(null);
    useEffect(() => {
      const svg = ref.current;
      if (!svg) return;
      while (svg.firstChild) svg.removeChild(svg.firstChild);
      const { W, H } = drawSwimlane(svg, sequenceSwimlane(t.seq));
      const base = { x: 0, y: 0, w: Math.max(W, 60), h: Math.max(H, 40) };
      const vb = { ...base };
      const apply = () => svg.setAttribute("viewBox", `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
      apply();

      const pt = (e) => {
        const r = svg.getBoundingClientRect();
        return { x: vb.x + ((e.clientX - r.left) / r.width) * vb.w,
                 y: vb.y + ((e.clientY - r.top) / r.height) * vb.h };
      };
      const onWheel = (e) => {
        e.preventDefault();
        const p = pt(e);
        const k = e.deltaY < 0 ? 0.85 : 1 / 0.85;
        const nw = Math.min(base.w * 4, Math.max(base.w / 40, vb.w * k));
        const s = nw / vb.w;
        vb.x = p.x - (p.x - vb.x) * s; vb.y = p.y - (p.y - vb.y) * s;
        vb.w = nw; vb.h = vb.h * s;
        apply();
      };
      let drag = null;
      const onDown = (e) => { drag = { ...pt(e) }; svg.style.cursor = "grabbing"; svg.setPointerCapture?.(e.pointerId); };
      const onMove = (e) => {
        if (!drag) return;
        const r = svg.getBoundingClientRect();
        vb.x = drag.x - ((e.clientX - r.left) / r.width) * vb.w;
        vb.y = drag.y - ((e.clientY - r.top) / r.height) * vb.h;
        apply();
      };
      const onUp = (e) => { drag = null; svg.style.cursor = "grab"; svg.releasePointerCapture?.(e.pointerId); };
      const onReset = () => { Object.assign(vb, base); apply(); };

      svg.style.cursor = "grab";
      svg.addEventListener("wheel", onWheel, { passive: false });
      svg.addEventListener("pointerdown", onDown);
      svg.addEventListener("pointermove", onMove);
      svg.addEventListener("pointerup", onUp);
      svg.addEventListener("pointerleave", onUp);
      svg.addEventListener("dblclick", onReset);
      return () => {
        svg.removeEventListener("wheel", onWheel);
        svg.removeEventListener("pointerdown", onDown);
        svg.removeEventListener("pointermove", onMove);
        svg.removeEventListener("pointerup", onUp);
        svg.removeEventListener("pointerleave", onUp);
        svg.removeEventListener("dblclick", onReset);
      };
    }, [t]);
    return html`<div class="swim"><div class="swim-lbl">${t.label}
      <span class="muted">· ${t.seq.length} passos · arraste para mover, roda para zoom, duplo-clique para reajustar</span></div>
      <svg ref=${ref} preserveAspectRatio="xMinYMin meet" style="touch-action:none"></svg></div>`;
  }

  function Timelines({ c }) {
    const tl = c.timelines || [];
    if (!tl.length) return html`<div class="note">Sem traces persistidas para este cluster
      (rode <code>run_typical_eval --emit-traces</code>).</div>`;
    return html`<div><h3 style="margin:16px 0 6px;font-size:14px">Linhas do tempo</h3>
      ${GROUPS.map(([kind, caption]) => {
        const items = tl.filter((t) => t.kind === kind);
        if (!items.length) return null;
        return html`<div class="tgroup"><div class="tcap">${caption}</div>
          ${items.map((t) => html`<${Swimlane} t=${t} />`)}</div>`;
      })}</div>`;
  }
  function QualityTable() {
    const rows = D.matrix;
    const cols = [["n_clusters", "nº cl"], ["dbcv", "DBCV"], ["silhouette", "silhouette"],
      ["purity", "purity"], ["nmi", "NMI"], ["ari", "ARI"]];
    const fmt = (k, v) => (v == null ? "—" : k === "n_clusters" ? v
      : k === "purity" ? pct(v) : f3(v));
    return html`<div class="panel">
      <h3 style="margin:0 0 6px;font-size:15px">Qualidade dos métodos de clustering</h3>
      <div class="muted" style="margin-bottom:8px">DBCV/silhouette em espaço UMAP-50
        (nulos para o consenso); purity/NMI/ARI vs tipo_procedimento.</div>
      <div style="overflow-x:auto"><table><thead><tr><th>arm · algo</th>
        ${cols.map(([, lbl]) => html`<th>${lbl}</th>`)}</tr></thead>
        <tbody>${rows.map((r) => html`<tr class=${r.arm === "anon" ? "anon" : ""}>
          <td><b>${r.arm}</b> · ${r.algo}</td>
          ${cols.map(([k]) => html`<td>${fmt(k, r.clustering?.[k])}</td>`)}</tr>`)}
        </tbody></table></div>
      <${Glossary} keys=${["dbcv", "silhouette", "purity", "nmi", "ari"]} />
      <div class="note">Leia como <b>não-inferioridade</b>: anon e raw ficam lado a lado —
        a anonimização não degrada a qualidade.</div></div>`;
  }

  function ModelMatrix() {
    const [metric, setMetric] = useState("top1");
    const rows = D.matrix;
    const best = {};
    D.models.forEach((m) => {
      const vals = rows.map((r) => r.weighted?.[m]?.[metric]).filter((v) => v != null);
      best[m] = metric === "suffix_dl" ? Math.min(...vals) : Math.max(...vals);
    });
    return html`<div class="panel">
      <h3 style="margin:0 0 6px;font-size:15px">Matriz de modelos (agregado por combo)</h3>
      <div class="togglebar">
        ${[["top1", "top-1 ↑"], ["top3", "top-3 ↑"], ["suffix_dl", "suffix DL ↓"],
          ["validity", "validity ↑"]].map(([k, lbl]) => html`
          <button class=${metric === k ? "on" : ""} onClick=${() => setMetric(k)}>${lbl}</button>`)}
      </div>
      <div style="overflow-x:auto"><table><thead><tr><th>arm · algo</th>
        ${D.models.map((m) => html`<th>${m}</th>`)}</tr></thead>
        <tbody>${rows.map((r) => html`<tr class=${r.arm === "anon" ? "anon" : ""}>
          <td><b>${r.arm}</b> · ${r.algo} <span class="muted">(${r.n_clusters_eval})</span></td>
          ${D.models.map((m) => {
            const v = r.weighted?.[m]?.[metric];
            const isBest = v != null && Math.abs(v - best[m]) < 1e-9;
            const ci = metric === "top1" && r.ci_top1?.[m];
            return html`<td style=${isBest ? "font-weight:700;color:var(--good)" : ""}>
              ${metric === "suffix_dl" ? f3(v) : pct(v)}
              ${ci && ci.lo != null ? html`<div class="ci">[${pct(ci.lo)}, ${pct(ci.hi)}]</div>` : ""}
            </td>`;
          })}</tr>`)}
        </tbody></table></div>
      <${Glossary} keys=${["top1", "top3", "suffix_dl", "validity"]} /></div>`;
  }

  function SizesPanel() {
    const b = D.size_buckets;
    if (!b || !b.length) return null;
    return html`<div class="panel">
      <h3 style="margin:0 0 4px;font-size:15px">Tamanho × qualidade</h3>
      <div class="muted" style="margin-bottom:10px">top-1 ponderado por cluster
        (${D.meta.named_run} · ${D.meta.named_algo}), agrupado por nº de traces.</div>
      <div style="overflow-x:auto"><table><thead><tr><th>traces/cluster</th><th>clusters</th>
        <th>% corpus</th><th>median test</th><th>Markov</th><th>GRU</th><th>GRU − Markov</th></tr></thead>
        <tbody>${b.map((r) => html`<tr>
          <td>${r.label}</td><td>${r.n_clusters}</td><td>${r.pct_corpus}%</td>
          <td>${r.median_test}</td><td>${pct(r.markov)}</td><td>${pct(r.gru)}</td>
          <td style=${r.gru_minus_markov > 0.005 ? "color:var(--good);font-weight:700" : "color:var(--mut)"}>
            ${r.gru_minus_markov >= 0 ? "+" : ""}${(r.gru_minus_markov * 100).toFixed(1)} pp</td>
        </tr>`)}</tbody></table></div>
      <${Glossary} keys=${["top1"]} />
      <div class="note">A vantagem neural só aparece acima de ~120 traces; para a maior parte
        do corpus a Markov-3 empata com a GRU — um resultado, não um defeito.</div></div>`;
  }

  function QualityPanel() {
    return html`<div><${QualityTable} /><${ModelMatrix} /><${SizesPanel} /></div>`;
  }
  const KIND_LABEL = {
    observado: "Observado — não é modelo (referência)",
    classico: "Modelos clássicos — treinados por contagem (CPU)",
    neural: "Modelos neurais — treinados por gradiente (GPU)",
    clustering: "Algoritmos de clustering",
    support: "Componentes de apoio",
  };
  const KIND_ORDER = ["observado", "classico", "neural", "clustering", "support"];

  function AlgosPanel() {
    const algos = D.algorithms || [];
    return html`<div>
      <div class="panel">
        <h3 style="margin:0 0 6px;font-size:15px">Pipeline comum (ponta a ponta)</h3>
        <div class="muted" style="margin-bottom:8px">Todo cluster e todo modelo saem desta
          sequência: do documento ao modelo de processo típico.</div>
        <ol class="pipe">${(D.pipeline || []).map((s) => html`<li>
          <b>${s.stage}</b> — ${s.does} <span class="muted">→ ${s.writes}</span></li>`)}</ol>
      </div>
      <div class="panel">
        <div class="note"><b>Treinado vs não-treinado.</b> <i>Real</i> e <i>Comum</i> são
          observações (o alvo), não modelos. Os <i>modelos</i> aprendem
          <code>P(próximo | contexto)</code> do treino e geram um percurso representativo —
          <b>clássicos</b> (Markov/DFG) por contagem, <b>neurais</b> (GRU/LSTM/Transformer)
          por gradiente. Empírico: Markov-3 ≈ GRU, exceto acima de ~120 traces.</div>
        ${KIND_ORDER.map((kind) => {
          const items = algos.filter((a) => a.kind === kind);
          if (!items.length) return null;
          return html`<div class="agroup"><h4>${KIND_LABEL[kind]}</h4>
            ${items.map((a) => html`<div class="acard">
              <div class="aname">${a.name}</div>
              <div><span class="alab">manipula</span> ${a.manipulation}</div>
              <div><span class="alab">parâmetros</span> ${a.params}</div>
              <div><span class="alab">arquitetura</span> ${a.architecture}</div>
            </div>`)}</div>`;
        })}
      </div></div>`;
  }

  function App() {
    const [tab, setTab] = useState("clusters");
    const m = D.meta;
    return html`<div class="wrap">
      <h1>Explorador de clusters & experimentos</h1>
      <p class="sub">SEAD-PI · clustering <code>${m.named_run}</code> ·
        raw × anon · modelos de processo típico por cluster</p>
      <div class="stats">
        <${Stat} v=${m.n_macro} label="clusters macro" />
        <${Stat} v=${m.n_evaluated} label="com modelos (≥30 traces)" />
        <${Stat} v=${f3(m.dbcv)} label="DBCV" title=${m.caveat} />
        <${Stat} v=${pct(m.purity)} label="purity vs tipo" />
        <${Stat} v=${f3(m.nmi)} label="NMI" />
        <${Stat} v=${f3(m.ari)} label="ARI" />
      </div>
      <div class="tabs">
        ${[["clusters", "Clusters"], ["quality", "Qualidade do clustering"], ["algos", "Algoritmos"]]
          .map(([k, lbl]) => html`<button class=${"tab" + (tab === k ? " on" : "")}
            onClick=${() => setTab(k)}>${lbl}</button>`)}
      </div>
      ${tab === "clusters" ? html`<${ClustersPanel} />`
        : tab === "quality" ? html`<${QualityPanel} />`
        : html`<${AlgosPanel} />`}
    </div>`;
  }

  render(html`<${App} />`, document.getElementById("app"));
})();
