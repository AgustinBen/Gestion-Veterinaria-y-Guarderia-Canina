type Props = {
  className?: string;
};

/** Marca de Huellitas: la patita del login, reutilizada en toda la app. */
export function PatitaIcon({ className }: Props) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      focusable="false"
      role="presentation"
      viewBox="0 0 52 52"
    >
      <circle cx="13" cy="18" r="5.5" />
      <circle cx="21" cy="11" r="5.5" />
      <circle cx="31" cy="11" r="5.5" />
      <circle cx="39" cy="18" r="5.5" />
      <path d="M26 23c8.3 0 15 6.5 15 13 0 5.2-4.1 8.5-9.2 8.5-2.1 0-3.5-1.1-5.8-1.1s-3.7 1.1-5.8 1.1c-5.1 0-9.2-3.3-9.2-8.5 0-6.5 6.7-13 15-13Z" />
    </svg>
  );
}
