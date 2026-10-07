#!/usr/bin/env node
// Thin Node.js wrapper for workflows that already use .mjs.
// It intentionally delegates NLP/model loading to the Python CLI, where all four
// parser ecosystems have their maintained APIs.
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const cli = path.join(here, 'deterministicFormaliser');
const r = spawnSync(cli, process.argv.slice(2), { stdio: 'inherit' });
if (r.error) {
  console.error(r.error.message);
  process.exit(1);
}
process.exit(r.status ?? 1);
