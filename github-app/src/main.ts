#!/usr/bin/env node
import { loadConfig } from "./config.js";
import { runForgeJob } from "./forgeRunner.js";
import { JobQueue } from "./queue.js";
import { createServer } from "./server.js";

const config = loadConfig();
const queue = new JobQueue(async (job) => {
  const result = await runForgeJob(job, { forgeCliPath: config.forgeCliPath });
  console.log(`forge job ${job.deliveryId}: draft PR ${result.prUrl}`);
});

createServer(config, queue).listen(config.port, () => {
  console.log(
    `Forge GitHub App listening on :${config.port}${config.webhookPath} ` +
      `(trigger label "${config.triggerLabel}")`
  );
});
