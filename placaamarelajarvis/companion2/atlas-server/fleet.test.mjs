import { test } from "node:test";
import assert from "node:assert/strict";
import { sanitizeFleet } from "./fleet.mjs";

test("fleet snapshot is bounded and normalized", () => {
  const fleet = sanitizeFleet({
    health: "ok\nspoof",
    working: "2",
    agents_list: [{ n: "Ops", st: "RUN", team: "ops", nwork: -4, head: "fila" }],
  });
  assert.equal(fleet.available, true);
  assert.equal(fleet.health, "ok spoof");
  assert.equal(fleet.working, 2);
  assert.deepEqual(fleet.agents_list[0], {
    n: "Ops",
    st: "RUN",
    act: "",
    nwork: 0,
    head: "fila",
    role: "",
    short: "",
    team: "ops",
  });
});
