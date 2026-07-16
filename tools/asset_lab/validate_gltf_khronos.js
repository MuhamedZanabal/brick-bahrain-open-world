#!/usr/bin/env node
'use strict';
const fs = require('fs');
const path = require('path');

async function main() {
  const [input, output] = process.argv.slice(2);
  if (!input || !output) throw new Error('usage: validate_gltf_khronos.js INPUT.glb OUTPUT.json');
  const validatorRoot = process.env.GLTF_VALIDATOR_ROOT;
  if (!validatorRoot) throw new Error('GLTF_VALIDATOR_ROOT is required');
  const validator = require(path.join(validatorRoot, 'node_modules', 'gltf-validator'));
  const report = await validator.validateBytes(new Uint8Array(fs.readFileSync(input)), {uri: input});
  fs.mkdirSync(path.dirname(output), {recursive: true});
  fs.writeFileSync(output, JSON.stringify(report, null, 2) + '\n');
  if ((report.issues?.numErrors ?? 0) !== 0) process.exitCode = 2;
}
main().catch((error) => { console.error(error); process.exit(3); });
