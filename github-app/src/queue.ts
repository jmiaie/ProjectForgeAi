import type { ForgeJob } from "./router.js";

export type JobHandler = (job: ForgeJob) => Promise<void>;

/**
 * In-process FIFO queue that runs one job at a time.
 *
 * Jobs are lost if the process exits. A durable queue is a ROADMAP "Next"
 * item; this is enough to answer GitHub within its 10 s webhook timeout
 * while the Forge run happens afterwards.
 */
export class JobQueue {
  private readonly pending: ForgeJob[] = [];
  private running: Promise<void> | null = null;

  constructor(
    private readonly handler: JobHandler,
    private readonly onError: (job: ForgeJob, err: unknown) => void = (job, err) =>
      console.error(`forge job ${job.deliveryId} failed:`, err)
  ) {}

  enqueue(job: ForgeJob): void {
    this.pending.push(job);
    if (!this.running) {
      this.running = this.drain().finally(() => {
        this.running = null;
      });
    }
  }

  get size(): number {
    return this.pending.length;
  }

  /** Resolves once every job enqueued so far has finished. */
  async idle(): Promise<void> {
    while (this.running) await this.running;
  }

  private async drain(): Promise<void> {
    let job: ForgeJob | undefined;
    while ((job = this.pending.shift())) {
      try {
        await this.handler(job);
      } catch (err) {
        this.onError(job, err);
      }
    }
  }
}
