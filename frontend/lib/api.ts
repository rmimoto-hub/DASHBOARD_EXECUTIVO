/** Cliente da API do comite executivo. */

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
// Nome da chave no localStorage — nao e segredo.
const CHAVE_TOKEN = "dir-dashboard.token"; // security-check: ok

export type Perfil = "ADMIN" | "USER" | "READ_ONLY";
export type Semaforo = "VERDE" | "AMBAR" | "VERMELHO" | "SEM_DADO";
export type TipoAcumulacao = "ACUMULA" | "TAXA";
export type Direcao = "MAIOR" | "MENOR";
export type Unidade =
  | "BRL" | "BRL_MIL" | "BRL_MI" | "PCT" | "NUM"
  | "DIAS" | "CLIENTES" | "PEDIDOS" | "LEADS";

export interface Usuario {
  id: number;
  nome: string;
  email: string;
  perfil: Perfil;
  ativo: boolean;
}

export interface Ciclo {
  id: number;
  ano: number;
  mes: number;
  semanas_total: number;
  semana_corrente: number;
  data_fechamento: string;
  status: string;
}

export interface LinhaRegional {
  regional_codigo: string;
  regional_nome: string;
  valor: string | null;
  meta: string | null;
  atingimento_pct: string | null;
  semaforo: Semaforo;
  desvio_pp: string | null;
}

export interface PontoSerie {
  semana: number;
  valor: string | null;
  valor_acumulado: string | null;
}

export interface Projecao {
  valor_projetado: string | null;
  atingimento_projetado_pct: string | null;
  gap: string | null;
  necessario_por_semana: string | null;
  esforco_vs_ritmo: string | null;
  semanas_restantes: number;
  alcancavel: boolean | null;
}

export interface LinhaPainel {
  codigo: string;
  nome: string;
  area: string;
  unidade: Unidade;
  tipo_acumulacao: TipoAcumulacao;
  melhor_direcao: Direcao;
  rotulo_numerador: string | null;
  rotulo_denominador: string | null;
  valor: string | null;
  numerador: string | null;
  denominador: string | null;
  meta: string | null;
  atingimento_pct: string | null;
  esperado_pct: string;
  desvio_pp: string | null;
  semaforo: Semaforo;
  projecao: Projecao;
  regionais: LinhaRegional[];
  serie: PontoSerie[];
}

export interface Painel {
  ciclo: Ciclo;
  semana: number;
  esperado_acumula_pct: string;
  linhas: LinhaPainel[];
}

export interface ItemPauta {
  posicao: number;
  codigo: string;
  nome: string;
  area: string;
  semaforo: Semaforo;
  atingimento_pct: string | null;
  esperado_pct: string;
  desvio_pp: string | null;
  regional_critica: string | null;
  desvio_regional_pp: string | null;
  projecao_pct: string | null;
}

export interface Pauta {
  ciclo: Ciclo;
  semana: number;
  itens: ItemPauta[];
}

export interface CelulaMatriz {
  regional_codigo: string;
  atingimento_pct: string | null;
  desvio_pp: string | null;
  semaforo: Semaforo;
}

export interface LinhaMatriz {
  codigo: string;
  nome: string;
  area: string;
  consolidado_semaforo: Semaforo;
  consolidado_desvio_pp: string | null;
  celulas: CelulaMatriz[];
}

export interface ResumoRegional {
  regional_codigo: string;
  regional_nome: string;
  verdes: number;
  ambares: number;
  vermelhos: number;
  sem_dado: number;
  desvio_medio_pp: string | null;
  status: "CRITICO" | "ATENCAO" | "NO_RITMO";
  kpis_criticos: string[];
}

export interface Matriz {
  ciclo: Ciclo;
  semana: number;
  regionais: { id: number; codigo: string; nome: string }[];
  linhas: LinhaMatriz[];
  resumo_regional: ResumoRegional[];
}

export interface Ocorrencia {
  cliente_rotulo: string;
  regional_codigo: string | null;
  causa: string;
  motivo: string;
  pedidos_afetados: number;
  plano_acao: string | null;
  responsavel: string | null;
}

export interface Titulo {
  posicao: number;
  cliente_rotulo: string;
  regional_codigo: string | null;
  consultor: string | null;
  valor_aberto: string;
  dias_atraso: number | null;
  em_negociacao: boolean;
  pct_do_total: string;
  pct_acumulado: string;
}

export interface Compromisso {
  id: number;
  frente: string;
  acao: string;
  responsavel: string;
  prazo: string;
  status: string;
  semana_origem: number;
  indicador_codigo: string | null;
  regional_codigo: string | null;
  resultado: string | null;
}

export interface Nota {
  semana: number;
  indicador_codigo: string | null;
  regional_codigo: string | null;
  texto: string;
}

export interface Detalhamento {
  dimensao: string;
  categoria: string;
  valor: string;
  regional_codigo: string | null;
  ordem: number;
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

function query(params: Record<string, string | number | undefined>): string {
  const q = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== "")
    .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
    .join("&");
  return q ? `?${q}` : "";
}

export async function login(email: string, senha: string): Promise<string> {
  const dados = await requisicao<{ access_token: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, senha }),
  });
  return dados.access_token;
}

export const buscarUsuarioLogado = () => requisicao<Usuario>("/auth/eu");

export const buscarCiclos = () =>
  requisicao<(Ciclo & { rotulo: string })[]>("/comite/ciclos");

export const buscarPainel = (ciclo?: number, semana?: number, area?: string) =>
  requisicao<Painel>(`/comite/painel${query({ ciclo_id: ciclo, semana, area })}`);

export const buscarKpi = (codigo: string, ciclo?: number, semana?: number) =>
  requisicao<LinhaPainel>(
    `/comite/painel/${codigo}${query({ ciclo_id: ciclo, semana })}`,
  );

export const buscarPauta = (ciclo?: number, semana?: number) =>
  requisicao<Pauta>(`/comite/pauta${query({ ciclo_id: ciclo, semana })}`);

export const buscarMatriz = (ciclo?: number, semana?: number) =>
  requisicao<Matriz>(`/comite/matriz${query({ ciclo_id: ciclo, semana })}`);

export const buscarOcorrencias = (ciclo?: number, semana?: number) =>
  requisicao<Ocorrencia[]>(
    `/comite/ocorrencias-entrega${query({ ciclo_id: ciclo, semana })}`,
  );

export const buscarInadimplentes = (ciclo?: number, semana?: number) =>
  requisicao<Titulo[]>(`/comite/inadimplentes${query({ ciclo_id: ciclo, semana })}`);

export const buscarCompromissos = (ciclo?: number) =>
  requisicao<Compromisso[]>(`/comite/compromissos${query({ ciclo_id: ciclo })}`);

export const buscarNotas = (ciclo?: number, semana?: number) =>
  requisicao<Nota[]>(`/comite/notas${query({ ciclo_id: ciclo, semana })}`);

export const buscarDetalhamentos = (
  codigo: string,
  dimensao?: string,
  ciclo?: number,
) =>
  requisicao<Detalhamento[]>(
    `/comite/detalhamentos/${codigo}${query({ dimensao, ciclo_id: ciclo })}`,
  );
