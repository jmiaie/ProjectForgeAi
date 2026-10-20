/** A Forge run requested by labelling an issue. */
export interface ForgeJob {
  deliveryId: string;
  repository: string; // owner/name
  issueNumber: number;
  issueBody: string;
  installationId?: number;
  requestedBy?: string;
}

export type RouteDecision =
  | { action: "enqueue"; job: ForgeJob }
  | { action: "ignore"; reason: string };

interface IssuesLabeledPayload {
  action?: string;
  label?: { name?: string };
  issue?: { number?: number; body?: string | null };
  repository?: { full_name?: string };
  installation?: { id?: number };
  sender?: { login?: string };
}

/**
 * Decide what to do with a verified webhook delivery. Pure: no I/O.
 * Only `issues` / `labeled` with the configured label starts a run.
 */
export function routeEvent(
  eventName: string | undefined,
  deliveryId: string,
  payload: unknown,
  triggerLabel: string
): RouteDecision {
  if (eventName !== "issues") {
    return { action: "ignore", reason: `event ${eventName ?? "(none)"} not handled` };
  }
  const p = (payload ?? {}) as IssuesLabeledPayload;
  if (p.action !== "labeled") {
    return { action: "ignore", reason: `issues.${p.action ?? "(none)"} not handled` };
  }
  if (p.label?.name !== triggerLabel) {
    return { action: "ignore", reason: `label ${p.label?.name ?? "(none)"} is not ${triggerLabel}` };
  }
  const repository = p.repository?.full_name;
  const issueNumber = p.issue?.number;
  if (!repository || typeof issueNumber !== "number") {
    return { action: "ignore", reason: "payload missing repository or issue number" };
  }
  return {
    action: "enqueue",
    job: {
      deliveryId,
      repository,
      issueNumber,
      issueBody: p.issue?.body ?? "",
      installationId: p.installation?.id,
      requestedBy: p.sender?.login,
    },
  };
}
