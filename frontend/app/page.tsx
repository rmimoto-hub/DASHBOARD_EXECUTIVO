"use client";

import Link from "next/link";

import { Cabecalho } from "@/components/Cabecalho";
import { CartaoKpi } from "@/components/CartaoKpi";
import { Carregando, Erro, Vazio } from "@/components/Estados";
import { Pastilha } from "@/components/Semaforo";
import { buscarNotas, buscarPainel, buscarPauta } from "@/lib/api";
import { formatarPP, rotuloArea } from "@/lib/formato";
import { usePagina } from "@/lib/sessao";

const ORDEM_AREAS = [
  "COMERCIAL",
  "OPERACOES",
  "ESTOQUE",
  "FINANCEIRO",
  "MARKETING",
];

export default function Painel() {
  const { usuario, dados, carregando, erro } = usePagina(async () => {
    const [painel, pauta, notas] = await Promise.all([
      buscarPainel(),
      buscarPauta(),
      buscarNotas(),
    ]);
    return { painel, pauta, notas };
  });

  if (carregando) return <Carregando texto="Carregando o painel…" />;
  if (erro) return <Erro mensagem={erro} />;
  if (!dados) return null;

  const { painel, pauta, notas } = dados;
  const notaGeral = notas.find((n) => n.indicador_codigo === null);

  const porArea = ORDEM_AREAS.map((area) => ({
    area,
    linhas: painel.linhas.filter((l) => l.area === area),
  })).filter((g) => g.linhas.length > 0);

  const contagem = {
    verde: painel.linhas.filter((l) => l.semaforo === "VERDE").length,
    ambar: painel.linhas.filter((l) => l.semaforo === "AMBAR").length,
    vermelho: painel.linhas.filter((l) => l.semaforo === "VERMELHO").length,
  };

  return (
    <>
      <Cabecalho
        ciclo={painel.ciclo}
        semana={painel.semana}
        usuario={usuario}
      />

      <main className="mx-auto max-w-[1600px] px-6 py-6">
        {/* Resumo em uma linha: quantos KPIs em cada estado */}
        <section className="mb-6 flex flex-wrap items-center gap-x-6 gap-y-2 rounded-lg border border-slate-200 bg-white px-5 py-3 text-sm">
          <span className="font-medium text-slate-700">
            {painel.linhas.length} indicadores
          </span>
          <span className="flex items-center gap-1.5 text-emerald-700">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
            {contagem.verde} no ritmo
          </span>
          <span className="flex items-center gap-1.5 text-amber-700">
            <span className="h-2.5 w-2.5 rounded-full bg-amber-500" />
            {contagem.ambar} em atenção
          </span>
          <span className="flex items-center gap-1.5 text-red-700">
            <span className="h-2.5 w-2.5 rounded-full bg-red-500" />
            {contagem.vermelho} fora do ritmo
          </span>
          <span className="ml-auto text-xs text-slate-400">
            ritmo esperado na semana {painel.semana}:{" "}
            {Math.round(Number(painel.esperado_acumula_pct))}% para
            indicadores que acumulam, 100% para taxas
          </span>
        </section>

        {notaGeral && (
          <p className="mb-6 border-l-2 border-kami bg-slate-50 px-4 py-3 text-sm text-slate-700">
            {notaGeral.texto}
          </p>
        )}

        {/* Pauta sugerida — por onde a reuniao comeca */}
        <section className="mb-8">
          <h2 className="mb-1 text-base font-semibold text-slate-800">
            Pauta sugerida
          </h2>
          <p className="mb-3 text-xs text-slate-500">
            Indicadores fora do ritmo, do maior desvio para o menor. A ação é
            sobre a regional apontada, não sobre a média.
          </p>

          {pauta.itens.length === 0 ? (
            <Vazio>Nenhum indicador fora do ritmo nesta semana.</Vazio>
          ) : (
            <ol className="divide-y divide-slate-100 overflow-hidden rounded-lg border border-slate-200 bg-white">
              {pauta.itens.map((item) => (
                <li key={item.codigo}>
                  <Link
                    href={`/kpi/${item.codigo}`}
                    className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3 text-sm transition hover:bg-slate-50"
                  >
                    <span className="w-5 shrink-0 text-right tabular-nums text-slate-400">
                      {item.posicao}
                    </span>
                    <Pastilha semaforo={item.semaforo} />
                    <span className="min-w-0 flex-1 font-medium text-slate-800">
                      {item.nome}
                    </span>
                    <span className="text-xs text-slate-400">
                      {rotuloArea(item.area)}
                    </span>
                    <span className="tabular-nums text-slate-600">
                      {item.atingimento_pct === null
                        ? "—"
                        : `${Math.round(Number(item.atingimento_pct))}%`}
                    </span>
                    <span className="w-20 text-right font-medium tabular-nums text-red-700">
                      {formatarPP(item.desvio_pp)}
                    </span>
                    <span className="w-32 text-right text-xs text-slate-500">
                      {item.regional_critica
                        ? `pior: ${item.regional_critica} (${formatarPP(item.desvio_regional_pp)})`
                        : ""}
                    </span>
                  </Link>
                </li>
              ))}
            </ol>
          )}
        </section>

        {/* Painel geral por area */}
        {porArea.map((grupo) => (
          <section key={grupo.area} className="mb-8">
            <h2 className="mb-3 text-base font-semibold text-slate-800">
              {rotuloArea(grupo.area)}
            </h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {grupo.linhas.map((linha) => (
                <CartaoKpi key={linha.codigo} linha={linha} />
              ))}
            </div>
          </section>
        ))}
      </main>
    </>
  );
}
