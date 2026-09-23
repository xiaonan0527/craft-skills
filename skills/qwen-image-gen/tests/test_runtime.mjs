import test from 'node:test';
import assert from 'node:assert/strict';
import { cpSync, mkdtempSync, readFileSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadSkillBundle, buildPlannerMessages, validatePlan, qualityCorrection } from '../runtime/core.mjs';

const skill = fileURLToPath(new URL('../', import.meta.url));
const options = { count: 1, width: 1152, height: 2048 };
const example = () => ({ items: [{ title: '青瓷茶杯', prompt: '一只青瓷茶杯放在白色桌面上，左侧自然光，杯子完整入镜。', category: '静物', traits: { style: '写实摄影', lighting: '左侧自然光' } }] });
function fixture(t) {
  const temp = mkdtempSync(join(tmpdir(), 'qwen-runtime-'));
  cpSync(skill, join(temp, 'skill'), { recursive: true });
  t.after(() => rmSync(temp, { recursive: true, force: true }));
  return { temp, dir: join(temp, 'skill') };
}

test('bundle is deterministic across location and changes when exact guidance bytes change', t => {
  const { dir } = fixture(t);
  const original = loadSkillBundle(skill);
  const copied = loadSkillBundle(dir);
  assert.equal(original.version, '0.3.0');
  assert.equal(original.digest, copied.digest);
  assert.ok(original.files.every(file => file.bytes > 0 && /^[a-f0-9]{64}$/.test(file.sha256)));
  const path = join(dir, 'references/rewriting.md');
  writeFileSync(path, readFileSync(path, 'utf8') + '\n');
  assert.notEqual(loadSkillBundle(dir).digest, original.digest);
});

test('runtime version is part of the pin', t => {
  const { dir } = fixture(t), before = loadSkillBundle(dir);
  const path = join(dir, 'runtime/manifest.json'), manifest = JSON.parse(readFileSync(path));
  manifest.version = '0.2.2';
  writeFileSync(path, JSON.stringify(manifest));
  assert.notEqual(loadSkillBundle(dir).digest, before.digest);
});

test('executable planner contract changes are also part of the pin', t => {
  const { dir } = fixture(t), before = loadSkillBundle(dir);
  const path = join(dir, 'runtime/core.mjs');
  writeFileSync(path, readFileSync(path, 'utf8') + '\n// Synthetic review fixture.\n');
  const after = loadSkillBundle(dir);
  assert.notEqual(after.digest, before.digest);
  assert.equal(after.instructions, before.instructions);
  assert.equal(after.files.at(-1).path, 'runtime/core.mjs');
});

test('bundle cannot import instruction files outside its directory', t => {
  const { temp, dir } = fixture(t);
  const outside = join(temp, 'outside.md');
  writeFileSync(outside, 'Neutral fixture, not a user file.');
  const path = join(dir, 'runtime/manifest.json'), manifest = JSON.parse(readFileSync(path));
  manifest.instructionFiles = ['../outside.md'];
  writeFileSync(path, JSON.stringify(manifest));
  assert.throws(() => loadSkillBundle(dir), { code: 'invalid_instruction_path' });
  symlinkSync(outside, join(dir, 'linked.md'));
  manifest.instructionFiles = ['linked.md'];
  writeFileSync(path, JSON.stringify(manifest));
  assert.throws(() => loadSkillBundle(dir), { code: 'invalid_instruction_path' });
});

test('private context stays in user messages and does not alter shared instructions or digest', () => {
  const bundle = loadSkillBundle(skill);
  const basic = buildPlannerMessages(bundle, { ...options, brief: '画一只红色茶杯' });
  const enriched = buildPlannerMessages(bundle, { ...options, brief: '画一只红色茶杯', preferences: { preferredColor: '蓝色' }, qualityContext: { issues: ['texture'], note: '茶杯边缘不要模糊' } });
  assert.equal(basic[0].content, enriched[0].content);
  assert.deepEqual(enriched.map(m => m.role), ['system', 'user']);
  const payload = JSON.parse(enriched[1].content);
  assert.equal(payload.originalBrief, '画一只红色茶杯');
  assert.equal(payload.preferences.preferredColor, '蓝色');
  assert.equal(bundle.digest, loadSkillBundle(skill).digest);
});

test('planning requires an original brief, valid budget, dimensions and reference description for edits', () => {
  const bundle = loadSkillBundle(skill);
  for (const brief of ['', '  ', null]) assert.throws(() => buildPlannerMessages(bundle, { ...options, brief }), { code: 'invalid_brief' });
  for (const count of [0, 13, 1.5]) assert.throws(() => buildPlannerMessages(bundle, { ...options, count, brief: '茶杯' }), { code: 'invalid_count' });
  assert.throws(() => buildPlannerMessages(bundle, { ...options, width: -1, brief: '茶杯' }), { code: 'invalid_dimensions' });
  assert.throws(() => buildPlannerMessages(bundle, { ...options, mode: 'edit', brief: '改成红色' }), { code: 'reference_description_required' });
  assert.equal(JSON.parse(buildPlannerMessages(bundle, { ...options, mode: 'edit', brief: '改成红色', referenceDescription: '白色桌上的蓝色茶杯' })[1].content).generation.mode, 'edit');
});

test('chunked batch context stays caller-owned and preserves the original brief verbatim', () => {
  const bundle = loadSkillBundle(skill), brief = '三种颜色的茶杯，各一张';
  const messages = buildPlannerMessages(bundle, { ...options, brief, exploration: 0.3, offset: 1, totalCount: 3, existingTitles: ['红色茶杯'] });
  const data = JSON.parse(messages[1].content);
  assert.equal(data.originalBrief, brief);
  assert.deepEqual(data.planningContext, { exploration: 0.3, offset: 1, totalCount: 3, existingTitles: ['红色茶杯'] });
  assert.throws(() => buildPlannerMessages(bundle, { ...options, brief, offset: 3, totalCount: 3 }), { code: 'invalid_batch_context' });
  assert.throws(() => buildPlannerMessages(bundle, { ...options, brief, exploration: 1.2 }), { code: 'invalid_exploration' });
});

test('valid model JSON is normalized and detached from source objects', () => {
  const input = example(), output = validatePlan(JSON.stringify(input), options);
  assert.deepEqual(output, input);
  output.items[0].traits.style = '水彩';
  assert.equal(input.items[0].traits.style, '写实摄影');
  assert.deepEqual(validatePlan(input, options), input);
});

test('model output cannot add tasks, routing, files or generation settings', () => {
  for (const key of ['url', 'route', 'endpoint', 'file', 'sourceId', 'seed', 'width', 'action', 'command']) {
    const input = example(); input.items[0][key] = 'model supplied';
    assert.throws(() => validatePlan(input, options), { code: 'invalid_item_fields' });
  }
  const input = example(); input.operations = [];
  assert.throws(() => validatePlan(input, options), { code: 'invalid_plan_fields' });
  assert.throws(() => validatePlan('```json\n' + JSON.stringify(example()) + '\n```', options), { code: 'invalid_plan_json' });
  assert.throws(() => validatePlan(example(), { ...options, count: 2 }), { code: 'plan_count_mismatch' });
});

test('T2I rejects reference tags while explicit edit mode permits them', () => {
  const input = example(); input.items[0].prompt = '将 <image1> 的蓝色茶杯改成红色。';
  assert.throws(() => validatePlan(input, options), { code: 'reference_tag_without_image' });
  assert.equal(validatePlan(input, { ...options, mode: 'edit' }).items.length, 1);
  input.items[0].prompt = 'A cup from < IMAGE 2 >.';
  assert.throws(() => validatePlan(input, options), { code: 'reference_tag_without_image' });
  for (const tag of ['<imageN>', '<image1/>', '</image1>']) {
    input.items[0].prompt = 'A cup from ' + tag;
    assert.throws(() => validatePlan(input, options), { code: 'reference_tag_without_image' });
  }
});

test('malformed item fields, excessive strings and unknown traits are rejected', () => {
  for (const [key, value, code] of [['title', 'x'.repeat(101), 'invalid_title'], ['prompt', '', 'invalid_prompt'], ['category', null, 'invalid_category']]) {
    const input = example(); input.items[0][key] = value;
    assert.throws(() => validatePlan(input, options), { code });
  }
  const input = example(); input.items[0].traits = { command: 'generate' };
  assert.throws(() => validatePlan(input, options), { code: 'invalid_traits' });
  input.items[0].traits = { style: { command: 'generate' } };
  assert.throws(() => validatePlan(input, options), { code: 'invalid_trait_value' });
  input.items[0].traits = JSON.parse('{"__proto__":"bad"}');
  assert.throws(() => validatePlan(input, options), { code: 'invalid_traits' });
});

test('quality corrections cover the eight stable issue IDs without imposing a medium or human limb count', () => {
  const ids = ['face', 'hands', 'anatomy', 'identity', 'adherence', 'texture', 'motion', 'other'];
  for (const id of ids) assert.ok(qualityCorrection({ issues: [id] }).length > 10);
  assert.equal(qualityCorrection({ issues: ['texture', 'texture'] }), qualityCorrection({ issues: ['texture'] }));
  assert.throws(() => qualityCorrection({ issues: ['taste'] }), { code: 'invalid_quality_issue' });
  assert.equal(qualityCorrection({}), '');
  const text = qualityCorrection({ issues: ['anatomy', 'texture'], note: '机器人原设定为四只手臂，有一只连接断开', correction: '保持水彩画风和四臂设定，修复关节连接' });
  assert.ok(text.includes('四臂设定'));
  assert.ok(!text.includes('exactly two'));
  assert.ok(!text.includes('photorealistic'));
});
