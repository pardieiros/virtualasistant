/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_SOCKET_HOST: string
  readonly VITE_SOCKET_PORT: string
  readonly VITE_SOCKET_KEY: string
  readonly VITE_SOCKET_USE_TLS: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}



