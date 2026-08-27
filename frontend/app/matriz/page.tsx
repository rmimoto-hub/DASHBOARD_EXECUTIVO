"use client";

import { Fragment } from "react";

import Link from "next/link";

import { Cabecalho } from "@/components/Cabecalho";
import { Carregando, Erro, Vazio } from "@/components/Estados";
import { buscarMatriz } from "@/lib/api";
import type { Semaforo } from "@/lib/api";
import {
  coresSemaforo,
  coresStatusRegional,
  formatarPP,
  rotuloArea,
} from "@/lib/formato";
import { usePagina } from "@/lib/sessao";

/** Fundo da celula da matriz — mais saturado que a pastilha, para ler de longe. */
function fundoCelula(s: Semaforo): string {
  switch (s) {
    case "VERDE":
      return "bg-emerald-100 text-emerald-900";
    case "AMBAR":
      return "bg-amber-100 text-amber-900";
    case "VERMELHO":
      return "bg-red-100 text-red-900";
    default:
      return "bg-slate-50 text-slate-400";
  }
}

export default function MatrizPagina() {
  const { usuario, dados, carregando, erro } = usePagina(() => buscarMatriz());

  if (carregando) return <Carregando texto="Carregando a matriz…" />;
  if (erro) return <Erro mensagem={erro} />;
  if (!dados) return null;

  const areas = [...new Set(dados.linhas.map((l) => l.area))];

  return (
    <>
      <Cabecalho ciclo={dados.ciclo} semana={dados.semana} usuario={usuario} />

      <main className="mx-auto max-w-[1600px] px-6 py-6">
        <h2 className="text-base font-semibold text-slate-800">
          Onde está a quebra
        </h2>
        <p className="mb-6 text-xs text-slate-500">
          Cada indicador contra cada regional. A cor compara o atingimento com
          o ritmo esperado da semana — não com 100% da meta do mês.
        </p>

        {/* Sintese por regional, derivada dos semaforos */}
        <section className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {dados.resumo_regional.map((r) => {
            const c = coresStatusRegional(r.status);
            return (
              <article
                key={r.regional_codigo}
                className={`rounded-lg border p-4 ${c.borda} ${c.fundo}`}
              >
                <div className="flex items-baseline justify-between">
                  <h3 className="text-lg font-semibold text-slate-900">
                    {r.regional_codigo}
                  </h3>
                  <span className={`text-sm font-medium ${c.texto}`}>
                    {c.rotulo}
                  </span>
                </div>
                <p className="mt-0.5 text-xs text-slate-500">
                  {r.regional_nome}
                </p>

                <div className="mt-3 flex gap-4 text-sm tabular-nums">
                  <span className="text-emerald-700">{r.verdes} no ritmo</span>
                  <span className="text-amber-700">{r.ambares} atenção</span>
                  <span className="text-red-700">{r.vermelhos} fora</span>
                </div>

                <p className="mt-2 text-xs text-slate-600">
                  desvio médio:{" "}
                  <strong className="tabular-nums">
                    {formatarPP(r.desvio_medio_pp)}
                  </strong>
                </p>

                {r.kpis_criticos.length > 0 && (
                  <p className="mt-2 text-[11px] leading-snug text-slate-500">
                    Fora do ritmo em: {r.kpis_criticos.length} indicadores
                  </p>
                )}
              </article>
            );
          })}
        </section>

        {/* A grade */}
        {dados.linhas.length === 0 ? (
          <Vazio>Nenhum indicador cadastrado neste ciclo.</Vazio>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
            <table className="w-full min-w-[720px] text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-4 py-2 text-left font-medium">Indicador</th>
                  <th className="px-3 py-2 text-center font-medium">
                    Consolidado
                  </th>
                  {dados.regionais.map((r) => (
                    <th
                      key={r.codigo}
                      className="px-3 py-2 text-center font-medium"
                    >
                      {r.codigo}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {areas.map((area) => (
                  <Fragment key={area}>
                    <tr className="bg-slate-50/60">
                      <td
                        colSpan={2 + dados.regionais.length}
                        className="px-4 py-1.5 text-xs font-medium uppercase tracking-wide text-slate-500"
                      >
                        {rotuloArea(area)}
                      </td>
                    </tr>
                    {dados.linhas
                      .filter((l) => l.area === area)
                      .map((linha) => (
                        <tr
                          key={linha.codigo}
                          className="border-b border-slate-100 last:border-0"
                        >
                          <td className="px-4 py-2">
                            <Link
                              href={`/kpi/${linha.codigo}`}
                              className="text-slate-800 hover:text-kami hover:underline"
                            >
                              {linha.nome}
                            </Link>
                          </td>
                          <td
                            className={`px-3 py-2 text-center tabular-nums ${fundoCelula(linha.consolidado_semaforo)}`}
                          >
                            {formatarPP(linha.consolidado_desvio_pp)}
                          </td>
                          {dados.regionais.map((reg) => {
                            const celula = linha.celulas.find(
                              (c) => c.regional_codigo === reg.codigo,
                            );
                            return (
                              <td
                                key={reg.codigo}
                                className={`px-3 py-2 text-center tabular-nums ${fundoCelula(celula?.semaforo ?? "SEM_DADO")}`}
                                title={
                                  celula?.atingimento_pct
                                    ? `${Math.round(Number(celula.atingimento_pct))}% da meta`
                                    : "sem dado"
                                }
                              >
                                {celula
                                  ? formatarPP(celula.desvio_pp)
                                  : "—"}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <p className="mt-3 text-xs text-slate-400">
          Os números são o desvio, em pontos percentuais, entre o atingimento e
          o ritmo esperado da semana. Passe o cursor para ver o atingimento.
        </p>
      </main>
    </>
  );
}
