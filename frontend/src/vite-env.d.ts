/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_MOCK_ROL?: string;
  readonly VITE_MOCK_TOKEN?: string;
  readonly VITE_MOCK_USUARIO?: string;
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
