import type { ReactNode } from 'react';

import type { SeccionId } from '../auth/permisos';

type Props = {
  seccion: SeccionId;
};

export function SeccionIcon({ seccion }: Props) {
  let dibujo: ReactNode;

  switch (seccion) {
    case 'panel':
      dibujo = <><rect x="3.5" y="3.5" width="7" height="7" rx="2" /><rect x="13.5" y="3.5" width="7" height="7" rx="2" /><rect x="3.5" y="13.5" width="7" height="7" rx="2" /><rect x="13.5" y="13.5" width="7" height="7" rx="2" /></>;
      break;
    case 'padron':
      dibujo = <><circle cx="9" cy="8" r="3" /><path d="M3.5 19v-1.2A4.8 4.8 0 0 1 8.3 13h1.4a4.8 4.8 0 0 1 4.8 4.8V19" /><path d="M16 5.2a3 3 0 0 1 0 5.6M17 13.4a4.6 4.6 0 0 1 3.5 4.4V19" /></>;
      break;
    case 'calendario':
      dibujo = <><rect x="3.5" y="5" width="17" height="15.5" rx="2.5" /><path d="M7.5 3.5v3M16.5 3.5v3M3.5 9.5h17M8 13h.01M12 13h.01M16 13h.01M8 16.5h.01M12 16.5h.01" /></>;
      break;
    case 'nueva-reserva':
      dibujo = <><circle cx="12" cy="12" r="8.5" /><path d="M12 8v8M8 12h8" /></>;
      break;
    case 'turnos':
      dibujo = <><circle cx="12" cy="12" r="8.5" /><path d="M12 7v5l3.5 2" /></>;
      break;
    case 'historia-clinica':
      dibujo = <><path d="M7 3.5h7l4 4V20a1.5 1.5 0 0 1-1.5 1.5h-9A1.5 1.5 0 0 1 6 20V5a1.5 1.5 0 0 1 1-1.5Z" /><path d="M14 3.5V8h4M12 11v6M9 14h6" /></>;
      break;
    case 'cobros':
      dibujo = <><rect x="3" y="5.5" width="18" height="14" rx="2.5" /><path d="M3 9.5h18M7 15h4M16.5 14.5h.01" /></>;
      break;
    case 'deudores':
      dibujo = <><circle cx="12" cy="12" r="8.5" /><path d="M15.5 8.5H10a2 2 0 0 0 0 4h4a2 2 0 0 1 0 4H8.5M12 6.5v11" /></>;
      break;
    case 'migracion':
      dibujo = <><path d="M7 7h13l-3-3M20 7l-3 3M17 17H4l3 3M4 17l3-3" /></>;
      break;
    case 'crear-cuenta':
      dibujo = <><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M19 8v6M22 11h-6" /></>;
      break;
  }

  return (
    <svg
      aria-hidden="true"
      fill="none"
      focusable="false"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.8"
      viewBox="0 0 24 24"
    >
      {dibujo}
    </svg>
  );
}
