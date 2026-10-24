import type { ChatMessage, MapNode, Material, NodeDetail, SessionSummary } from '../types';

/** Demo content: a lecture on backpropagation. Replace freely — nothing else depends on it. */

const daysAgo = (d: number) => new Date(Date.now() - d * 86_400_000).toISOString();

export const DEMO_MATERIALS: Material[] = [
  { id: 'm1', name: 'Lecture3_Backprop.pdf', kind: 'pdf', label: 'Lecture slides' },
  { id: 'm2', name: 'CW1_Handout.pdf', kind: 'pdf', label: 'Assessment handout' },
  { id: 'm3', name: 'notes_photo.jpg', kind: 'image', label: 'Photo of notes' },
  { id: 'm4', name: 'Tutorial2.pdf', kind: 'pdf', label: 'Tutorial sheet' },
];

export const DEMO_SESSIONS: SessionSummary[] = [
  { id: 's-backprop', title: 'Backpropagation', topic: 'Neural networks', updatedAt: daysAgo(0), durationMin: 23 },
  { id: 's-cw1', title: 'CW1 handout walkthrough', topic: 'Coursework 1', updatedAt: daysAgo(2) },
  { id: 's-activation', title: 'Activation functions', topic: 'Neural networks', updatedAt: daysAgo(3) },
  { id: 's-optim', title: 'Optimisers: SGD and Adam', topic: 'Neural networks', updatedAt: daysAgo(5) },
  { id: 's-bayes', title: "Bayes' rule", topic: 'Probability', updatedAt: daysAgo(12) },
  { id: 's-dist', title: 'Common distributions', topic: 'Probability', updatedAt: daysAgo(15) },
];

export const N = {
  root: { id: 'root', parentId: null, label: 'Backpropagation', subtitle: "Find each weight's share of the error", status: 'normal', order: 0 },
  forward: { id: 'forward', parentId: 'root', label: 'Forward pass', status: 'new', order: 0 },
  save: { id: 'save', parentId: 'forward', label: "Save each layer's output", status: 'new', order: 0 },
  loss: { id: 'loss', parentId: 'root', label: 'Loss', status: 'new', hiddenChildren: 2, order: 1 },
  chain: { id: 'chain', parentId: 'root', label: 'Chain rule', status: 'new', order: 2 },
  update: { id: 'update', parentId: 'root', label: 'Weight update', status: 'new', order: 3 },
  local: { id: 'local', parentId: 'chain', label: 'Local gradient per layer', status: 'new', order: 0 },
  back: { id: 'back', parentId: 'chain', label: 'Pass gradient back', status: 'new', order: 1 },
} satisfies Record<string, MapNode>;

/** The finished map, used when reopening the demo session from the sidebar. */
export const FINISHED_MAP: MapNode[] = [
  N.root,
  { ...N.forward, status: 'normal' },
  { ...N.save, status: 'normal' },
  { ...N.loss, status: 'normal' },
  { ...N.chain, status: 'normal' },
  {
    ...N.update,
    status: 'corrected',
    correction: { said: 'backprop updates weights', actually: 'Backprop finds gradients. The optimiser (SGD) updates weights.' },
  },
  { ...N.local, status: 'normal' },
  { ...N.back, status: 'normal' },
];

const t = (min: number) => new Date(Date.now() - min * 60_000).toISOString();

export const NODE_DETAILS: Record<string, Omit<NodeDetail, 'nodeId'> & { messages: ChatMessage[] }> = {
  root: {
    title: 'Backpropagation',
    breadcrumb: [],
    source: { materialId: 'm1', fileName: 'Lecture3_Backprop.pdf', page: 2, context: 'Lecture 3 · Overview', quote: 'Backpropagation computes the gradient of the loss with respect to every weight in the network.' },
    summary: 'A way to work out how much each weight contributed to the error, so we know which way to nudge it.',
    messages: [],
  },
  forward: {
    title: 'Forward pass',
    breadcrumb: ['Backpropagation'],
    source: { materialId: 'm1', fileName: 'Lecture3_Backprop.pdf', page: 6, context: 'Lecture 3 · Forward pass', quote: 'Inputs flow layer by layer to the output; intermediate activations are stored.' },
    summary: 'Data goes in, flows through each layer, and comes out as a prediction. We keep each layer’s output for later.',
    messages: [],
  },
  save: {
    title: "Save each layer's output",
    breadcrumb: ['Backpropagation', 'Forward pass'],
    source: { materialId: 'm1', fileName: 'Lecture3_Backprop.pdf', page: 7, context: 'Lecture 3 · Caching', quote: 'The stored activations are reused when computing gradients in the backward pass.' },
    summary: 'Saving outputs now means we don’t have to recompute them when we go backwards.',
    messages: [],
  },
  loss: {
    title: 'Loss',
    breadcrumb: ['Backpropagation'],
    source: { materialId: 'm1', fileName: 'Lecture3_Backprop.pdf', page: 9, context: 'Lecture 3 · Loss', quote: 'The loss measures how far the prediction is from the target.' },
    summary: 'One number that says how wrong the prediction was. Backprop starts from here.',
    messages: [],
  },
  chain: {
    title: 'Chain rule',
    breadcrumb: ['Backpropagation'],
    source: { materialId: 'm1', fileName: 'Lecture3_Backprop.pdf', page: 14, context: 'Lecture 3 · Backpropagation', quote: "Each layer's error = the error from the layer after × its own local gradient." },
    summary: "To get a gradient deep in the network, multiply small pieces together, one layer at a time, starting from the loss. That's the chain rule.",
    messages: [
      { id: 'c1', role: 'user', text: 'Why does it go backwards, not forwards?', at: t(6) },
      { id: 'c2', role: 'assistant', text: 'Each layer needs the piece from the layer after it. Starting at the loss means that piece is always ready.', at: t(6) },
      { id: 'c3', role: 'user', text: 'So it reuses work?', at: t(5) },
      { id: 'c4', role: 'assistant', text: 'Exactly — that reuse is why backprop is fast. I’ve added "Pass gradient back" to your map.', at: t(5) },
    ],
  },
  update: {
    title: 'Weight update',
    breadcrumb: ['Backpropagation'],
    source: { materialId: 'm1', fileName: 'Lecture3_Backprop.pdf', page: 18, context: 'Lecture 3 · Training loop', quote: 'The optimiser uses the gradients to update the weights, e.g. w ← w − η∇L.' },
    summary: 'Backprop only finds the gradients. A separate step — the optimiser, like SGD — uses them to change the weights.',
    messages: [
      { id: 'u1', role: 'user', text: 'I think backprop is the step that updates the weights.', at: t(8) },
      { id: 'u2', role: 'assistant', text: 'Nearly! Backprop finds the gradients — the optimiser updates the weights.', at: t(8) },
    ],
  },
  local: {
    title: 'Local gradient per layer',
    breadcrumb: ['Backpropagation', 'Chain rule'],
    source: { materialId: 'm1', fileName: 'Lecture3_Backprop.pdf', page: 15, context: 'Lecture 3 · Local gradients', quote: 'Each layer only needs the derivative of its own output with respect to its input.' },
    summary: 'Every layer only has to know its own small slope. The chain rule joins them up.',
    messages: [],
  },
  back: {
    title: 'Pass gradient back',
    breadcrumb: ['Backpropagation', 'Chain rule'],
    source: { materialId: 'm1', fileName: 'Lecture3_Backprop.pdf', page: 16, context: 'Lecture 3 · Backward pass', quote: 'Gradients are propagated from the output layer back towards the input.' },
    summary: 'Each layer hands its gradient to the layer before it, so no work is repeated.',
    messages: [],
  },
};
