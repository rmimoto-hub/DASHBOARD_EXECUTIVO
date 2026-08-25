import type { ResumoIndicador } from "@/lib/api";
import {
  ehVariacaoBoa,
  formatarCompetencia,
  formatarValor,
  formatarVariacao,
} from "@/lib/formato";

export function CartaoIndicador({ item }: { item: ResumoIndicador }) {
  const variacaoBoa = ehVariacaoBoa(item.variacao_pct, item.melhor_direcao);

  const corVariacao =
    variacaoBoa === null
      ? "text-slate-500"
      : variacaoBoa
        ? "text-emerald-600"
        : "text-red-600";

  const atingimento = item.atingimento_pct;

  return (
    <article className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-medium text-slate-600">{item.nome}</h3>
        <span className="shrink-0 rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
          {item.area}
        </span>
      </div>

      <p className="mt-3 text-2xl font-semibold tabular-nums text-slate-900">
        {formatarValor(item.valor, item.unidade)}
      </p>

      <div className="mt-2 flex items-baseline gap-2 text-sm">
        <span className={`font-medium tabular-nums ${corVariacao}`}>
          {formatarVariacao(item.variacao_pct)}
        </span>
        <span className="text-slate-400">vs. mes anterior</span>
      </div>

      <dl className="mt-4 space-y-1 border-t border-slate-100 pt-3 text-xs text-slate-500">
        <div className="flex justify-between">
          <dt>Meta</dt>
          <dd className="tabular-nums">
            {formatarValor(item.meta, item.unidade)}
          </dd>
        </div>
        <div className="flex justify-between">
          <dt>Atingimento</dt>
          <dd className="tabular-nums">
            {atingimento === null
              ? "—"
              : `${atingimento.toLocaleString("pt-BR", { maximumFractionDigits: 0 })}%`}
          </dd>
        </div>
        <div className="flex justify-between">
          <dt>Competencia</dt>
          <dd>{formatarCompetencia(item.competencia)}</dd>
        </div>
      </dl>
    </article>
  );
}
