"use client";

import Link from "next/link";

import { Anel } from "@/components/Anel";
import type { LinhaPainel } from "@/lib/api";
import {
  coresSemaforo,
  formatarPP,
  formatarValor,
  frasePrjecao,
} from "@/lib/formato";

/**
 * Um KPI no painel geral.
 *
 * A ordem de leitura segue o ritual: o valor realizado primeiro, o
 * atingimento no anel, e o desvio do ritmo por ultimo — que e o que
 * decide se o assunto entra na pauta.
 */
export function CartaoKpi({ linha }: { linha: LinhaPainel }) {
  const c = coresSemaforo(linha.semaforo);
  const ating = linha.atingimento_pct ? Number(linha.atingimento_pct) : null;
  const pior = [...linha.regionais]
    .filter((r) => r.desvio_pp !== null)
    .sort((a, b) => Number(a.desvio_pp) - Number(b.desvio_pp))[0];

  return (
    <Link
      href={`/kpi/${linha.codigo}`}
      className={`group flex flex-col rounded-lg border bg-white p-4 transition hover:shadow-md ${c.borda}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-medium text-slate-700">
            {linha.nome}
          </h3>
          <p className="mt-2 text-2xl font-semibold tabular-nums text-slate-900">
            {formatarValor(linha.valor, linha.unidade)}
          </p>
          <p className="mt-0.5 text-xs text-slate-400">
            meta {formatarValor(linha.meta, linha.unidade)}
          </p>
        </div>
        <Anel
          atingimento={ating}
          esperado={Number(linha.esperado_pct)}
          semaforo={linha.semaforo}
          tamanho={76}
        />
      </div>

      <div className={`mt-3 rounded px-2 py-1.5 text-xs ${c.fundo} ${c.texto}`}>
        <span className="font-medium">{c.rotulo}</span>
        {linha.desvio_pp !== null && (
          <>
            {" · "}
            {formatarPP(linha.desvio_pp)} vs ritmo de{" "}
            {Math.round(Number(linha.esperado_pct))}%
          </>
        )}
      </div>

      <dl className="mt-3 space-y-1 border-t border-slate-100 pt-2 text-xs">
        {linha.tipo_acumulacao === "ACUMULA" &&
          linha.projecao.atingimento_projetado_pct !== null && (
            <div className="flex justify-between gap-2">
              <dt className="text-slate-500">Projeção de fechamento</dt>
              <dd className="shrink-0 font-medium tabular-nums text-slate-700">
                {Math.round(Number(linha.projecao.atingimento_projetado_pct))}%
              </dd>
            </div>
          )}
        {pior && (
          <div className="flex justify-between gap-2">
            <dt className="text-slate-500">Regional mais atrasada</dt>
            <dd className="shrink-0 font-medium text-slate-700">
              {pior.regional_codigo} ({formatarPP(pior.desvio_pp)})
            </dd>
          </div>
        )}
      </dl>

      {linha.tipo_acumulacao === "ACUMULA" && (
        <p className="mt-2 text-[11px] leading-snug text-slate-400">
          {frasePrjecao(
            linha.tipo_acumulacao,
            linha.projecao.esforco_vs_ritmo,
            linha.projecao.alcancavel,
            linha.projecao.semanas_restantes,
          )}
        </p>
      )}
    </Link>
  );
}
