import IntakeWizard from '@/components/IntakeWizard';

export default function ConnectionsPage() {
  return (
    <main className="p-6">
      <IntakeWizard onComplete={() => undefined} />
    </main>
  );
}
