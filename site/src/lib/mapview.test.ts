import test from "node:test";
import assert from "node:assert/strict";
import { rot, unrot, fitBox, pathPoints, C } from "./mapview.ts";

test("giro de 45° como no minimapa do jogo: x + y para a direita, x − y para baixo", () => {
  const [u0, v0] = rot(100, 100);
  const [u1, v1] = rot(110, 110);   // x e y crescem: só para a direita
  assert.ok(u1 > u0 && Math.abs(v1 - v0) < 1e-9);
  const [u2, v2] = rot(110, 100);   // só x cresce: direita e para baixo
  assert.ok(u2 > u0 && v2 > v0);
  assert.deepEqual(rot(C, C), [C, C]);
  const [x, y] = unrot(...rot(37, 201));
  assert.ok(Math.abs(x - 37) < 1e-9 && Math.abs(y - 201) < 1e-9);
});

test("enquadramento quadrado com margem e lado mínimo", () => {
  assert.deepEqual(fitBox([[10, 20], [30, 25]], 5, 10), { x: 5, y: 7.5, size: 30 });   // centro (20; 22,5), lado 20 + 2 × 5
  assert.equal(fitBox([[0, 0]], 0, 40)!.size, 40);
  assert.equal(fitBox([]), null);
  assert.equal(pathPoints("M1,2 3,4ZM5.5,-0.5 6,7Z").length, 4);
});
