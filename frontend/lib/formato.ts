/** Formatacao de numeros para exibicao, em pt-BR. */

export function formatarValor(
  valor: string | null,
  unidade: string,
): string {
  if (valor === null) return "—";
  const n = Number(valor);
  if (Number.isNaN(n)) return "—";

  switch (unidade) {
    case "BRL":
      return n.toLocaleString("pt-BR", {
        style: "currency",
        currency: "BRL",
        maximumFractionDigits: 0,
      });
    case "PCT":
      return `${n.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
    case "DIAS":
      return `${n.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} dias`;
    default:
      return n.toLocaleString("pt-BR", { maximumFractionDigits: 1 });
  }
}

export function formatarVariacao(pct: number | null): string {
  if (pct === null) return "—";
  const sinal = pct > 0 ? "+" : "";
  return `${sinal}${pct.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
}

export function formatarCompetencia(competencia: string | null): string {
  if (!competencia) return "sem dados";
  // competencia vem como YYYY-MM-DD; monta a data em horario local para
  // evitar o deslocamento de fuso que new Date("YYYY-MM-DD") causa.
  const [ano, mes] = competencia.split("-").map(Number);
  return new Date(ano, mes - 1, 1).toLocaleDateString("pt-BR", {
    month: "short",
    year: "numeric",
  });
}

/**
 * Se a variacao foi para o lado bom do indicador.
 * Ex: inadimplencia caindo e bom (melhor_direcao = MENOR).
 */
export function ehVariacaoBoa(
  pct: number | null,
  melhorDirecao: "MAIOR" | "MENOR",
): boolean | null {
  if (pct === null || pct === 0) return null;
  return melhorDirecao === "MAIOR" ? pct > 0 : pct < 0;
}
