import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

const source = readFileSync(new URL('../src/components/map/layout.ts', import.meta.url), 'utf8');
const javascript = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 } }).outputText;
const { layoutTree } = await import(`data:text/javascript,${encodeURIComponent(javascript)}`);

const root = { id: 'root', parentId: null, label: 'Root', status: 'normal', order: 0 };
const first = { id: 'first', parentId: 'root', label: 'First', status: 'new', order: 0 };
const second = { id: 'second', parentId: 'root', label: 'Second', status: 'new', order: 1 };
const initial = layoutTree([root, first]);
const expanded = layoutTree([root, first, second], initial);
for (const id of ['root', 'first']) {
  const before = initial.boxes.find((box) => box.node.id === id);
  const after = expanded.boxes.find((box) => box.node.id === id);
  assert.deepEqual([after.x, after.y], [before.x, before.y]);
}
const newcomer = expanded.boxes.find((box) => box.node.id === 'second');
assert.ok(newcomer.y >= expanded.boxes.find((box) => box.node.id === 'first').y + 56);
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
assert.ok(get('b1').y >= get('a2').y + get('a2').h + 60);
assert.ok(get('first').y + get('first').h < get('second').y);
assert.ok(grouped.edges.every(edge => edge.d.includes(' C') && !edge.d.includes(' V')));
const manuallyPlaced = layoutTree(branches.map(node => node.id === 'a1' ? { ...node, position: { x: 900, y: 440 } } : node));
assert.equal(manuallyPlaced.boxes.find(box => box.node.id === 'a1').y, 440);
assert.equal(manuallyPlaced.boxes.find(box => box.node.id === 'a1').x, 900);
const wideLevel = [root, first, ...Array.from({ length: 198 }, (_, i) => ({ ...second, id: `topic${i}`, order: i + 1 }))];
const wide = layoutTree(wideLevel, initial);
assert.equal(wide.boxes.length, 200);
for (const id of ['root', 'first']) {
  const before = initial.boxes.find(box => box.node.id === id);
  const after = wide.boxes.find(box => box.node.id === id);
  assert.deepEqual([after.x, after.y], [before.x, before.y]);
}
const siblings = wide.boxes.filter(box => box.node.parentId === 'root').sort((a, b) => a.y - b.y);
for (let i = 1; i < siblings.length; i++) assert.ok(siblings[i].y >= siblings[i - 1].y + siblings[i - 1].h);
