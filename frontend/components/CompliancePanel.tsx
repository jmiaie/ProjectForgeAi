'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { apiGet, apiPost, type ComplianceProfile } from '@/lib/api';
import { StatusBadge } from '@/components/StatusBadge';

type AuditEvent = {
  id: string;
  action: string;
  allowed: boolean;
  reason: string;
};

type CompliancePanelProps = {
  projectId: string;
  initialProfile?: ComplianceProfile;
};

export function CompliancePanel({ projectId, initialProfile }: CompliancePanelProps) {
  const [profile, setProfile] = useState<ComplianceProfile | undefined>(initialProfile);
  const [category, setCategory] = useState(initialProfile?.category || 'standard');
  const [events, setEvents] = useState<AuditEvent[]>([]);

  const saveProfile = async () => {
    const result = await apiPost<ComplianceProfile>(
      `/api/v1/projects/${projectId}/compliance/profile`,
      { category },
    );
    setProfile(result);
    await loadAudit();
  };

  const loadAudit = async () => {
    const result = await apiGet<{ events: AuditEvent[] }>(
      `/api/v1/projects/${projectId}/compliance/audit`,
    );
    setEvents(result.events);
  };

  return (
    <Card className="panel">
      <div className="panel-header">
        <div>
          <div className="eyebrow">Governance</div>
          <h2>Compliance</h2>
          <p className="muted">Profile-driven redaction, memory gates, and audit events.</p>
        </div>
        <StatusBadge status={profile?.category || 'standard'} />
      </div>
      <div className="stack">
        <select className="input" value={category} onChange={(event) => setCategory(event.target.value)}>
          <option value="standard">standard</option>
          <option value="hipaa">hipaa</option>
          <option value="legal">legal</option>
          <option value="soc2">soc2</option>
          <option value="gdpr">gdpr</option>
        </select>
        <div className="row">
          <Button onClick={saveProfile}>Save profile</Button>
          <Button variant="outline" onClick={loadAudit}>Load audit</Button>
        </div>
        <div className="grid grid-2">
          <div className="stat">
            <strong>Memory writes</strong>
            <p className="muted">{profile?.allow_memory_writes === false ? 'Blocked' : 'Allowed'}</p>
          </div>
          <div className="stat">
            <strong>LLM redaction</strong>
            <p className="muted">{profile?.redact_before_llm ? 'Enabled' : 'Not required'}</p>
          </div>
        </div>
        {events.length ? (
          <ul className="list">
            {events.slice(-5).map((event) => (
              <li key={event.id}>
                {event.action}: {event.reason}
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </Card>
  );
}
