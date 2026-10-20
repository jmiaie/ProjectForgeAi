import { describe, expect, it } from "vitest";
import { JobQueue } from "./queue.js";
import type { ForgeJob } from "./router.js";

const job = (n: number): ForgeJob => ({
  deliveryId: `d-${n}`,
  repository: "octo/repo",
  issueNumber: n,
  issueBody: "",
});

describe("JobQueue", () => {
  it("runs jobs one at a time in order and survives a failing job", async () => {
    const seen: number[] = [];
    const errors: string[] = [];
    let active = 0;
    const q = new JobQueue(
      async (j) => {
        active++;
        expect(active).toBe(1);
        await new Promise((r) => setTimeout(r, 5));
        active--;
        if (j.issueNumber === 2) throw new Error("boom");
        seen.push(j.issueNumber);
      },
      (j, err) => errors.push(`${j.deliveryId}:${(err as Error).message}`)
    );
    q.enqueue(job(1));
    q.enqueue(job(2));
    q.enqueue(job(3));
    await q.idle();
    expect(seen).toEqual([1, 3]);
    expect(errors).toEqual(["d-2:boom"]);
  });
});
