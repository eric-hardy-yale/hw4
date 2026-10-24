// Swatch colors for the catalogue's color names.
const SWATCH: Record<string, string> = {
  navy: '#0b2545', 'navy blue': '#0b2545', blue: '#1f5fae', 'royal blue': '#2251c4', 'light blue': '#9cc3ea',
  white: '#ffffff', ivory: '#fffbeb', cream: '#f5eedc', black: '#111111', red: '#b3261e', green: '#2e7d32',
  yellow: '#f2c94c', gold: '#c9a227', 'dusty coral': '#e48f7f', gray: '#9aa0a6', 'light gray': '#cfd4da',
  'heather gray': '#b8bcc2', 'dark heather gray': '#5f6368', 'charcoal gray': '#4a4e54',
  'dark heather charcoal': '#44474c', 'heather charcoal gray': '#55595e',
  multicolor: 'conic-gradient(#b3261e, #f2c94c, #2e7d32, #1f5fae, #b3261e)',
}

export const swatch = (name: string) => SWATCH[name.toLowerCase()] ?? '#d0d4da'
