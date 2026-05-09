'use client';

import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

export default function IntakeWizard({ onComplete }: { onComplete: () => void }) {
  const [step] = useState(0);
  const recommended = ['google', 'microsoft', 'slack', 'github', 'mcp_server'];

  const handleConnect = async (type: string) => {
    console.log(`Connecting to ${type} at step ${step}...`);
    // TODO: call backend /api/v1/intake/connections
  };

  return (
    <Card className="mx-auto max-w-2xl p-8">
      <h1 className="mb-8 text-3xl font-bold">Connect Your Tools</h1>
      <div className="grid grid-cols-2 gap-4">
        {recommended.map((tool) => (
          <Button
            key={tool}
            variant="outline"
            className="h-24 flex-col"
            onClick={() => handleConnect(tool)}
          >
            <span className="text-lg capitalize">{tool}</span>
          </Button>
        ))}
      </div>
      <Button onClick={onComplete} className="mt-8 w-full">
        Skip &amp; Continue
      </Button>
    </Card>
  );
}
