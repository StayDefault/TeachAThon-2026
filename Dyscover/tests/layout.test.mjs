import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

const source = readFileSync(new URL('../src/components/map/layout.ts', import.meta.url), 'utf8');
const javascript = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 } }).outputText;
const { crossLinks, layoutTree } = await import(`data:text/javascript,${encodeURIComponent(javascript)}`);

const root = { id: 'root', parentId: null, label: 'Root', status: 'normal', order: 0 };
const first = { id: 'first', parentId: 'root', label: 'First', status: 'new', order: 0 };
const second = { id: 'second', parentId: 'root', label: 'Second', status: 'new', order: 1 };
const initial = layoutTree([root, first]);
const expanded = layoutTree([root, first, second], initial);
const newcomer = expanded.boxes.find((box) => box.node.id === 'second');
const rootBox = expanded.boxes.find((box) => box.node.id === 'root');
const firstChild = expanded.boxes.find((box) => box.node.id === 'first');
assert.ok(newcomer.y >= firstChild.y + firstChild.h + 24);
assert.equal(rootBox.y + rootBox.h / 2, (firstChild.y + firstChild.h / 2 + newcomer.y + newcomer.h / 2) / 2);
const corrected = layoutTree([root, { ...first, status: 'corrected' }, second], expanded);
const firstBox = corrected.boxes.find((box) => box.node.id === 'first');
const secondBox = corrected.boxes.find((box) => box.node.id === 'second');
assert.ok(secondBox.y >= firstBox.y + firstBox.h + 24);

const branches = [root, first, second,
  { id: 'a1', parentId: 'first', label: 'First child', status: 'normal', order: 0 },
  { id: 'a2', parentId: 'first', label: 'Second child', status: 'normal', order: 1 },
  { id: 'b1', parentId: 'second', label: 'Other branch', status: 'normal', order: 0 }];
const grouped = layoutTree(branches);
const get = id => grouped.boxes.find(box => box.node.id === id);
for (const parent of [root, first, second]) {
  const children = grouped.boxes.filter(box => box.node.parentId === parent.id);
  if (!children.length) continue;
  assert.ok(children.every(box => box.x === get(parent.id).x + 380));
  assert.equal(get(parent.id).y + get(parent.id).h / 2,
    (children[0].y + children[0].h / 2 + children.at(-1).y + children.at(-1).h / 2) / 2);
}
assert.ok(get('b1').y >= get('a2').y + get('a2').h + 60);
assert.ok(get('first').y + get('first').h < get('second').y);
assert.ok(grouped.edges.every(edge => edge.d.includes(' C') && !edge.d.includes(' V')));
const crowded = layoutTree([root, first, second,
  { id: 'b1', parentId: 'second', label: 'Other branch', status: 'normal', order: 0 }]);
const expandedBranch = layoutTree([...branches], crowded);
const branchBox = id => expandedBranch.boxes.find(box => box.node.id === id);
assert.ok(branchBox('a2').y >= branchBox('a1').y + branchBox('a1').h + 24);
assert.ok(branchBox('b1').y >= branchBox('a2').y + branchBox('a2').h + 24);
assert.equal(branchBox('first').y + branchBox('first').h / 2,
  (branchBox('a1').y + branchBox('a1').h / 2 + branchBox('a2').y + branchBox('a2').h / 2) / 2);
const scattered = { ...crowded, boxes: [...crowded.boxes, { node: branches[3], depth: 2, x: 760, y: 500, w: 250, h: 64 }] };
const regrouped = layoutTree(branches, scattered);
const position = id => regrouped.boxes.find(box => box.node.id === id);
assert.equal(position('a2').y, position('a1').y + position('a1').h + 28);
assert.ok(position('b1').y >= position('a2').y + position('a2').h + 24 || position('b1').y + position('b1').h + 24 <= position('a1').y);
const manuallyPlaced = layoutTree(branches.map(node => node.id === 'a1' ? { ...node, position: { x: 900, y: 440 } } : node));
assert.equal(manuallyPlaced.boxes.find(box => box.node.id === 'a1').y, 440);
assert.equal(manuallyPlaced.boxes.find(box => box.node.id === 'a1').x, 900);
const wideLevel = [root, first, ...Array.from({ length: 198 }, (_, i) => ({ ...second, id: `topic${i}`, order: i + 1 }))];
const wide = layoutTree(wideLevel, initial);
assert.equal(wide.boxes.length, 200);
const siblings = wide.boxes.filter(box => box.node.parentId === 'root').sort((a, b) => a.y - b.y);
for (let i = 1; i < siblings.length; i++) assert.ok(siblings[i].y >= siblings[i - 1].y + siblings[i - 1].h);
const wideRoot = wide.boxes.find(box => box.node.id === 'root');
assert.equal(wideRoot.y + wideRoot.h / 2,
  (siblings[0].y + siblings[0].h / 2 + siblings.at(-1).y + siblings.at(-1).h / 2) / 2);
const links = crossLinks(grouped.boxes, [{ id: 'e1', from: 'a1', to: 'b1', label: 'causes' }, { id: 'gone', from: 'a1', to: 'missing', label: 'x' }]);
assert.equal(links.length, 1);
assert.match(links[0].d, /^M.* Q/);
assert.ok(links[0].y > get('a1').y && links[0].y < get('b1').y + get('b1').h);
const understoodBox = layoutTree([root, { ...first, mastery: 'understood', learnerWords: 'my words' }]).boxes.find(box => box.node.id === 'first');
assert.ok(understoodBox.h > 64);

