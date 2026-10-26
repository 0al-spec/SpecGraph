"use strict";
const $ = id => document.getElementById(id);
const NS = "http://www.w3.org/2000/svg";
let data = null, selection = null, fingerprint = "", scale = 1, tx = 0, ty = 0;
let graphSize = {width: 800, height: 500}, initialized = false, drag = null, following = true;
function svg(tag, attrs = {}, text = null) {
  const node = document.createElementNS(NS, tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, String(value));
  if (text !== null) node.textContent = text;
  return node;
}
function element(tag, className, text) {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
}
function transform() {
  $("scene").setAttribute("transform", `translate(${tx} ${ty}) scale(${scale})`);
  $("zoom-value").textContent = `${Math.round(scale * 100)}%`;
}
function fit() {
  const rect = $("canvas").getBoundingClientRect();
  scale = Math.min(1.05, Math.max(.15, Math.min((rect.width - 70) / graphSize.width, (rect.height - 190) / graphSize.height)));
  tx = (rect.width - graphSize.width * scale) / 2;
  ty = 145 + Math.max(0, (rect.height - 190 - graphSize.height * scale) / 2);
  transform();
}
function zoom(factor, cx = $("canvas").clientWidth / 2, cy = $("canvas").clientHeight / 2) {
  following = false;
  const next = Math.max(.15, Math.min(2.5, scale * factor));
  tx = cx - (cx - tx) * next / scale;
  ty = cy - (cy - ty) * next / scale;
  scale = next;
  transform();
}
function selectNode(id) {
  selection = id;
  document.querySelectorAll(".note").forEach(node => {
    const selected = node.dataset.id === id;
    node.classList.toggle("selected", selected);
    node.setAttribute("aria-pressed", String(selected));
  });
  const note = data?.nodes.find(node => node.id === id);
  $("selection-empty").hidden = Boolean(note);
  $("selection").hidden = !note;
  if (!note) return;
  $("selected-id").textContent = note.id;
  $("selected-label").textContent = note.label;
  $("selected-detail").textContent = note.detail || "A short thought, ready to grow.";
  $("sources").replaceChildren();
  for (const source of note.sources) {
    const card = element("div", "source-card", "");
    const meta = element("div", "source-meta", "");
    meta.append(element("span", "speaker", source.speaker), element("code", "", source.ref));
    card.append(meta, element("blockquote", "", source.quote));
    $("sources").append(card);
  }
  $("relations").replaceChildren();
  const related = data.links.filter(link => link.source_id === id || link.target_id === id);
  if (related.length) $("relations").append(element("h3", "", "Connections"));
  const endpoint = nodeId => {
    const node = data.nodes.find(item => item.id === nodeId);
    return `${node?.label || nodeId}${node ? "" : " · outside this branch"}`;
  };
  for (const link of related) {
    $("relations").append(element("p", "relation-row", `${endpoint(link.source_id)} — ${link.label} → ${endpoint(link.target_id)}`));
  }
}
function render(snapshot) {
  data = snapshot;
  const nodes = snapshot.nodes;
  $("node-count").textContent = `${nodes.length} ${nodes.length === 1 ? "thought" : "thoughts"}`;
  $("revision").textContent = snapshot.revision ? `revision ${snapshot.revision.slice(0, 12)}` : "No saved revision";
  $("revision").dataset.revision = snapshot.revision || "";
  $("revision").dataset.renderedAt = String(Date.now());
  $("empty").hidden = nodes.length > 0;
  $("scene").replaceChildren();
  if (!nodes.length) { selectNode(null); return; }
  const byId = new Map(nodes.map(node => [node.id, node]));
  const children = new Map(nodes.map(node => [node.id, []]));
  const roots = [];
  for (const node of nodes) {
    if (children.has(node.parent_id)) children.get(node.parent_id).push(node.id);
    else roots.push(node.id);
  }
  const positions = new Map();
  // Iterative postorder supports deep sketches without overflowing the JS stack.
  const pending = roots.slice().reverse().map(id => [id, 0, false]);
  let leaf = 0, maxDepth = 0;
  while (pending.length) {
    const [id, depth, visited] = pending.pop();
    const descendants = children.get(id);
    if (!visited && descendants.length) {
      pending.push([id, depth, true]);
      descendants.slice().reverse().forEach(child => pending.push([child, depth + 1, false]));
      continue;
    }
    const y = descendants.length ? (positions.get(descendants[0]).y + positions.get(descendants.at(-1)).y) / 2 : leaf++ * 104;
    positions.set(id, {x: depth * 270, y});
    maxDepth = Math.max(maxDepth, depth);
  }
  graphSize = {width: maxDepth * 270 + 224, height: Math.max(1, leaf - 1) * 104 + 72};
  function edge(from, to, related = false) {
    const a = positions.get(from), b = positions.get(to);
    if (!a || !b) return;
    const x1 = a.x + 224, y1 = a.y + 36, x2 = b.x, y2 = b.y + 36;
    const midpoint = (x1 + x2) / 2;
    $("scene").append(svg("path", {d: `M${x1},${y1} C${midpoint},${y1} ${midpoint},${y2} ${x2},${y2}`, class: related ? "edge related" : "edge"}));
  }
  for (const node of nodes) if (byId.has(node.parent_id)) edge(node.parent_id, node.id);
  for (const link of snapshot.links) edge(link.source_id, link.target_id, true);
  for (const node of nodes) {
    const point = positions.get(node.id);
    const group = svg("g", {class: `note${roots.includes(node.id) ? " root" : ""}`, transform: `translate(${point.x} ${point.y})`, tabindex: 0, role: "button", "aria-label": node.label, "aria-pressed": selection === node.id ? "true" : "false"});
    group.dataset.id = node.id;
    group.append(svg("rect", {width: 224, height: 72, rx: 12}), svg("circle", {cx: 18, cy: 22, r: 3, class: "node-point"}));
    const words = [...node.label];
    const line = words.length > 24 ? words.slice(0, 23).join("") + "…" : node.label;
    group.append(svg("text", {x: 30, y: 27}, line), svg("text", {x: 18, y: 52, class: "node-caption"}, node.id.slice(0, 31)), svg("title", {}, node.label));
    group.addEventListener("click", () => selectNode(node.id));
    group.addEventListener("keydown", event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); selectNode(node.id); } });
    $("scene").append(group);
  }
  selectNode(byId.has(selection) ? selection : roots[0]);
  if (!initialized || following) { fit(); initialized = true; }
  else transform();
}
function showState(state, warning) {
  const labels = {current: "Live", empty: "Ready for notes", stale: "Showing saved view", unavailable: "Notes unavailable"};
  $("status").textContent = labels[state] || "Connection interrupted";
  $("status-dot").className = `dot ${["current", "empty"].includes(state) ? "live" : "warn"}`;
  $("notice").hidden = !warning;
  $("notice").textContent = warning || "";
  if (!data && warning) {
    $("empty").querySelector("h2").textContent = "Waiting for a readable sketch.";
    $("empty").querySelector("p").textContent = "The view will reconnect automatically.";
  } else {
    $("empty").querySelector("h2").textContent = "Your thoughts start here.";
    $("empty").querySelector("p").textContent = "Saved notes will appear as the conversation unfolds.";
  }
}
async function refresh() {
  try {
    const response = await fetch("/api/notes", {cache: "no-store"});
    if (!response.ok) throw new Error("Preview read failed");
    const result = await response.json();
    $("sketch-name").textContent = result.sketch;
    const next = result.snapshot ? JSON.stringify(result.snapshot) : "";
    if (next && next !== fingerprint) { render(result.snapshot); fingerprint = next; }
    showState(result.display_state, result.warning);
  } catch {
    showState(data ? "stale" : "unavailable", "Connection interrupted. Your last saved view is preserved; reconnecting…");
  } finally { setTimeout(refresh, 650); }
}
$("fit").addEventListener("click", () => { following = true; fit(); });
$("zoom-in").addEventListener("click", () => zoom(1.2));
$("zoom-out").addEventListener("click", () => zoom(1 / 1.2));
$("canvas").addEventListener("wheel", event => { event.preventDefault(); const rect = $("canvas").getBoundingClientRect(); zoom(event.deltaY < 0 ? 1.12 : 1 / 1.12, event.clientX - rect.left, event.clientY - rect.top); }, {passive: false});
$("canvas").addEventListener("pointerdown", event => { if (event.target.closest(".note")) return; following = false; drag = {x: event.clientX, y: event.clientY, tx, ty}; $("canvas").setPointerCapture(event.pointerId); });
$("canvas").addEventListener("pointermove", event => { if (!drag) return; tx = drag.tx + event.clientX - drag.x; ty = drag.ty + event.clientY - drag.y; transform(); });
$("canvas").addEventListener("pointerup", () => { drag = null; });
$("canvas").addEventListener("pointercancel", () => { drag = null; });
$("canvas").addEventListener("keydown", event => {
  if (event.target !== $("canvas")) return;
  const moves = {ArrowLeft: [30, 0], ArrowRight: [-30, 0], ArrowUp: [0, 30], ArrowDown: [0, -30]};
  if (moves[event.key]) { event.preventDefault(); tx += moves[event.key][0]; ty += moves[event.key][1]; transform(); }
});
new ResizeObserver(() => { if (initialized) fit(); }).observe($("canvas"));
refresh();
