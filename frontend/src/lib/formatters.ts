export function formatZAR(amount: number): string {
  return 'R' + amount.toLocaleString('en-ZA', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

export function formatDuration(hours: number): string {
  if (hours < 1) {
    return Math.round(hours * 60) + ' min';
  }
  return hours.toFixed(1) + ' hrs';
}
