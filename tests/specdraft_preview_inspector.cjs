"use strict";

// Exercise the shipped app and its click handlers against a minimal DOM double.
// This checks inspector text semantics, not browser layout or accessibility.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

class Element {
  constructor(tag) {
    this.tag = tag;
    this.children = [];
    this.dataset = {};
    this.attributes = {};
    this.listeners = {};
    this.classList = {toggle() {}};
  }
  set innerHTML(_) { throw new Error("Inspector content must remain literal text"); }
  setAttribute(name, value) { this.attributes[name] = value; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  addEventListener(name, handler) { this.listeners[name] = handler; }
  getBoundingClientRect() { return {width: 1200, height: 800}; }
}

function inspector(nodes, links) {
  const ids = new Map();
  const document = {
    getElementById(id) {
      if (!ids.has(id)) ids.set(id, new Element("div"));
      return ids.get(id);
    },
    createElement: tag => new Element(tag),
    createElementNS: (_, tag) => new Element(tag),
    querySelectorAll: () => [],
  };
  const context = vm.createContext({
    document,
    // Keep the app's initial network refresh pending; render the selected fixture.
    fetch: () => new Promise(() => {}),
    ResizeObserver: class { observe() {} },
  });
  const app = path.join(__dirname, "../tools/specdraft_preview/static/app.js");
  vm.runInContext(fs.readFileSync(app, "utf8"), context, {filename: app});
  context.snapshot = {revision: "fixture", nodes, links};
  vm.runInContext("render(snapshot)", context);
  return id => {
    const card = ids.get("scene").children.find(node => node.dataset.id === id);
    assert.ok(card, `Missing rendered note ${id}`);
    card.listeners.click();
    return ids.get("relations").children
      .filter(node => node.className === "relation-row")
      .map(node => node.textContent);
  };
}

const note = (id, label) => ({id, label, detail: "", parent_id: null, sources: []});

test("selecting either endpoint preserves the original source, label and target", () => {
  const select = inspector([note("a", "Alpha"), note("b", "Beta")], [
    {source_id: "a", label: "depends on", target_id: "b"},
  ]);
  assert.deepEqual(select("a"), ["Alpha — depends on → Beta"]);
  assert.deepEqual(select("b"), ["Alpha — depends on → Beta"]);
});

test("incoming and outgoing links retain their direction outside the selected branch", () => {
  const select = inspector([note("b", "Beta")], [
    {source_id: "outside_a", label: "depends on", target_id: "b"},
    {source_id: "b", label: "provides", target_id: "outside_c"},
  ]);
  assert.deepEqual(select("b"), [
    "outside_a · outside this branch — depends on → Beta",
    "Beta — provides → outside_c · outside this branch",
  ]);
});

test("a self-link is shown once with both endpoints", () => {
  const select = inspector([note("a", "Alpha")], [
    {source_id: "a", label: "refers to", target_id: "a"},
  ]);
  assert.deepEqual(select("a"), ["Alpha — refers to → Alpha"]);
});

test("endpoint names and relationship labels remain literal inspector text", () => {
  const select = inspector([note("a", "<b>Alpha</b>"), note("b", "<script>Beta</script>")], [
    {source_id: "a", label: "<i>depends on</i>", target_id: "b"},
  ]);
  assert.deepEqual(select("b"), ["<b>Alpha</b> — <i>depends on</i> → <script>Beta</script>"]);
});
