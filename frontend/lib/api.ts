/** Cliente da API do backend. */

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
// Nome da chave no localStorage — nao e segredo.
const CHAVE_TOKEN = "dir-dashboard.token"; // security-check: ok

export type Perfil = "ADMIN" | "USER" | "READ_ONLY";

export interface Usuario {
  id: number;
  nome: string;
  email: string;
  perfil: Perfil;
  ativo: boolean;
  ultimo_acesso: string | null;
}

export interface ResumoIndicador {
  codigo: string;
  nome: string;
  area: string;
  unidade: string;
  melhor_direcao: "MAIOR" | "MENOR";
  competencia: string | null;
  valor: string | null;
  meta: string | null;
  valor_anterior: string | null;
  variacao_pct: number | null;
  atingimento_pct: number | null;
}

export class ErroApi extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export function guardarToken(token: string) {
  localStorage.setItem(CHAVE_TOKEN, token);
}

export function lerToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(CHAVE_TOKEN);
}

export function limparToken() {
  localStorage.removeItem(CHAVE_TOKEN);
}

async function requisicao<T>(caminho: string, init?: RequestInit): Promise<T> {
  const token = lerToken();
  const resposta = await fetch(`${BASE}${caminho}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });

  if (!resposta.ok) {
    let detalhe = `Erro ${resposta.status}`;
    try {
      const corpo = await resposta.json();
      if (corpo?.detail) detalhe = corpo.detail;
    } catch {
      // resposta sem JSON — mantem a mensagem padrao
    }
    throw new ErroApi(resposta.status, detalhe);
  }

  return resposta.json() as Promise<T>;
}

export async function login(email: string, senha: string): Promise<string> {
  const dados = await requisicao<{ access_token: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, senha }),
  });
  return dados.access_token;
}

export function buscarUsuarioLogado(): Promise<Usuario> {
  return requisicao<Usuario>("/auth/eu");
}

export function buscarResumo(area?: string): Promise<ResumoIndicador[]> {
  const query = area ? `?area=${encodeURIComponent(area)}` : "";
  return requisicao<ResumoIndicador[]>(`/indicadores/resumo${query}`);
}
