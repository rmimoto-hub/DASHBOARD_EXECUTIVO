/** Formatacao para leitura executiva, em pt-BR. */
import type { Semaforo, Unidade } from "./api";

const num = (v: number, casas = 0) =>
  v.toLocaleString("pt-BR", {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
  });

/**
 * Formata o valor de um KPI conforme sua unidade.
 *
 * Atencao: PCT vem da API como razao (0.923), nao como 92.3 — a
 * conversao acontece aqui, num lugar so.
 */
export function formatarValor(
  valor: string | number | null,
  unidade: Unidade,
): string {
  if (valor === null) return "—";
  const n = typeof valor === "string" ? Number(valor) : valor;
  if (Number.isNaN(n)) return "—";

  switch (unidade) {
    case "BRL":
      return `R$ ${num(n)}`;
    case "BRL_MIL":
      return `R$ ${num(n)} mil`;
    case "BRL_MI":
      return `R$ ${num(n, 2)} mi`;
    case "PCT":
      return `${num(n * 100, 1)}%`;
    case "DIAS":
      return `${num(n, 1)} dias`;
    case "CLIENTES":
      return `${num(n)} clientes`;
    case "PEDIDOS":
      return `${num(n)} pedidos`;
    case "LEADS":
      return `${num(n)} leads`;
    default:
      // Sem casa decimal forcada: uma contagem de ganhos e "23", nao "23,0".
      return n.toLocaleString("pt-BR", { maximumFractionDigits: 1 });
  }
}

/** Um percentual de atingimento, que ja vem em escala 0-100. */
export function formatarPct(valor: string | number | null, casas = 0): string {
  if (valor === null) return "—";
  const n = typeof valor === "string" ? Number(valor) : valor;
  return Number.isNaN(n) ? "—" : `${num(n, casas)}%`;
}

/** Pontos percentuais, sempre com sinal — o desvio do ritmo. */
export function formatarPP(valor: string | number | null): string {
  if (valor === null) return "—";
  const n = typeof valor === "string" ? Number(valor) : valor;
  if (Number.isNaN(n)) return "—";
  return `${n > 0 ? "+" : ""}${num(n, 0)} p.p.`;
}

export function formatarData(iso: string): string {
  const [ano, mes, dia] = iso.split("-").map(Number);
  return new Date(ano, mes - 1, dia).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
  });
}

const MESES = [
  "janeiro", "fevereiro", "março", "abril", "maio", "junho",
  "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
];

export const nomeMes = (mes: number) => MESES[mes - 1] ?? String(mes);

export const AREAS: Record<string, string> = {
  COMERCIAL: "Comercial",
  OPERACOES: "Operações",
  ESTOQUE: "Estoque",
  FINANCEIRO: "Financeiro",
  MARKETING: "Marketing",
};

export const rotuloArea = (area: string) => AREAS[area] ?? area;

/** Classes do semaforo. Um objeto por uso — nao compartilhar referencia. */
export function coresSemaforo(s: Semaforo): {
  texto: string;
  fundo: string;
  borda: string;
  pastilha: string;
  rotulo: string;
} {
  switch (s) {
    case "VERDE":
      return {
        texto: "text-emerald-700",
        fundo: "bg-emerald-50",
        borda: "border-emerald-200",
        pastilha: "bg-emerald-500",
        rotulo: "No ritmo",
      };
    case "AMBAR":
      return {
        texto: "text-amber-700",
        fundo: "bg-amber-50",
        borda: "border-amber-200",
        pastilha: "bg-amber-500",
        rotulo: "Atenção",
      };
    case "VERMELHO":
      return {
        texto: "text-red-700",
        fundo: "bg-red-50",
        borda: "border-red-200",
        pastilha: "bg-red-500",
        rotulo: "Fora do ritmo",
      };
    default:
      return {
        texto: "text-slate-500",
        fundo: "bg-slate-50",
        borda: "border-slate-200",
        pastilha: "bg-slate-300",
        rotulo: "Sem dado",
      };
  }
}

export function coresStatusRegional(status: string): {
  texto: string;
  fundo: string;
  borda: string;
  rotulo: string;
} {
  switch (status) {
    case "CRITICO":
      return {
        texto: "text-red-700",
        fundo: "bg-red-50",
        borda: "border-red-300",
        rotulo: "Crítico",
      };
    case "ATENCAO":
      return {
        texto: "text-amber-700",
        fundo: "bg-amber-50",
        borda: "border-amber-300",
        rotulo: "Atenção",
      };
    default:
      return {
        texto: "text-emerald-700",
        fundo: "bg-emerald-50",
        borda: "border-emerald-300",
        rotulo: "No ritmo",
      };
  }
}

/**
 * Explica em uma frase o que a projecao significa.
 * TAXA nao extrapola — a posicao atual e a estimativa de fechamento.
 */
export function frasePrjecao(
  tipo: "ACUMULA" | "TAXA",
  esforco: string | null,
  alcancavel: boolean | null,
  semanasRestantes: number,
): string {
  if (semanasRestantes === 0) return "Ciclo encerrado.";
  if (tipo === "TAXA") {
    return alcancavel
      ? "Taxa dentro da meta."
      : "Taxa fora da meta; não há acúmulo a recuperar.";
  }
  if (esforco === null) return "Sem ritmo apurado.";
  const e = Number(esforco);
  if (e <= 0) return "Meta já alcançada.";
  const vezes = e.toLocaleString("pt-BR", { maximumFractionDigits: 2 });
  const semana = semanasRestantes === 1 ? "na semana final" : `nas ${semanasRestantes} semanas restantes`;
  return alcancavel
    ? `Exige ${vezes}× o ritmo atual ${semana}.`
    : `Exigiria ${vezes}× o ritmo atual ${semana} — fora de alcance.`;
}
