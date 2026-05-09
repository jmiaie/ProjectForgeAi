type StatusBadgeProps = {
  status: string | boolean;
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const value = typeof status === 'boolean' ? (status ? 'ready' : 'pending') : status;
  const normalized = value.toLowerCase();
  const className =
    normalized === 'healthy' || normalized === 'connected' || normalized === 'completed' || normalized === 'ready'
      ? 'badge badge-success'
      : normalized === 'pending' || normalized === 'not_connected' || normalized === 'missing'
        ? 'badge badge-warning'
        : 'badge';

  return <span className={className}>{value.replace('_', ' ')}</span>;
}
