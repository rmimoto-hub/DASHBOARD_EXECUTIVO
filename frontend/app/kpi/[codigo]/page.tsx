"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { Anel } from "@/components/Anel";
import { Cabecalho } from "@/components/Cabecalho";
import { Carregando, Erro, Vazio } from "@/components/Estados";
import { Pastilha } from "@/components/Semaforo";
import {
  buscarDetalhamentos,
  buscarKpi,
  buscarNotas,
  buscarPainel,
  type Detalhamento,
} from "@/lib/api";
import {
  coresSemaforo,
  formatarPP,
  formatarValor,
  frasePrjecao,
  rotuloArea,
} from "@/lib/formato";
import { usePagina } from "@/lib/sessao";

export default function DetalheKpi() {
  const params = useParams<{ codigo: string }>();
  const codigo = params.codigo;

  const { usuario, dados, carregando, erro } = usePagina(
    async () => {
      const [kpi, painel, notas, detalhes] = await Promise.all([
        buscarKpi(codigo),
        buscarPainel(),
        buscarNotas(),
        buscarDetalhamentos(codigo).catch(() => []),
      ]);
      return { kpi, painel, notas, detalhes };
    },
    [codigo],
  );

  if (carregando) return <Carregando texto="Carregando o indicador…" />;
  if (erro) return <Erro mensagem={erro} />;
  if (!dados) return null;

  const { kpi, painel, notas, detalhes } = dados;
  const c = coresSemaforo(kpi.semaforo);
  const ating = kpi.atingimento_pct ? Number(kpi.atingimento_pct) : null;
  const nota = notas.find((n) => n.indicador_codigo === codigo);

  const maxSerie = Math.max(
    ...kpi.serie.map((p) =>
      Math.abs(Number(p.valor_acumulado ?? p.valor ?? 0)),
    ),
    Number(kpi.meta ?? 0),
    1,
  );

  const porDimensao = detalhes.reduce<Record<string, Detalhamento[]>>(
    (acc, d) => {
      (acc[d.dimensao] ??= []).push(d);
      return acc;
    },
    {},
  );

  return (
    <>
      <Cabecalho ciclo={painel.ciclo} semana={painel.semana} usuario={usuario} />

      <main className="mx-auto max-w-[1400px] px-6 py-6">
        <Link
          href="/"
          className="text-sm text-slate-500 transition hover:text-kami"
        >
          ← voltar ao painel
        </Link>

        <div className="mt-3 flex flex-wrap items-start justify-between gap-6">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-400">
              {rotuloArea(kpi.area)} ·{" "}
              {kpi.tipo_acumulacao === "ACUMULA"
                ? "acumula no mês"
                : "taxa"}{" "}
              · melhor {kpi.melhor_direcao === "MAIOR" ? "maior" : "menor"}
            </p>
            <h2 className="mt-1 text-2xl font-semibold text-slate-900">
              {kpi.nome}
            </h2>
          </div>
          <Anel
            atingimento={ating}
            esperado={Number(kpi.esperado_pct)}
            semaforo={kpi.semaforo}
            tamanho={104}
          />
        </div>

        {/* 1. Quanto realizamos */}
        <section className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Bloco rotulo="Realizado no mês">
            {formatarValor(kpi.valor, kpi.unidade)}
          </Bloco>
          <Bloco rotulo="Meta do mês">
            {formatarValor(kpi.meta, kpi.unidade)}
          </Bloco>
          <Bloco rotulo={`Ritmo esperado na semana ${painel.semana}`}>
            {Math.round(Number(kpi.esperado_pct))}%
          </Bloco>
          <Bloco rotulo="Desvio do ritmo" destaque={c.texto}>
            {formatarPP(kpi.desvio_pp)}
          </Bloco>
        </section>

        {/* A razao, quando o indicador e uma taxa */}
        {kpi.denominador !== null && (
          <p className="mt-3 text-xs text-slate-500">
            {formatarValor(kpi.numerador, "NUM")}{" "}
            {kpi.rotulo_numerador ?? "numerador"} sobre{" "}
            {formatarValor(kpi.denominador, "NUM")}{" "}
            {kpi.rotulo_denominador ?? "denominador"} — o consolidado é
            ponderado pelo volume, não a média das regionais.
          </p>
        )}

        {/* 2. Projecao */}
        {kpi.tipo_acumulacao === "ACUMULA" && (
          <section className="mt-6 rounded-lg border border-slate-200 bg-white p-5">
            <h3 className="text-sm font-semibold text-slate-800">
              Projeção de fechamento
            </h3>
            <div className="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Bloco rotulo="No ritmo atual, fecha em">
                {kpi.projecao.atingimento_projetado_pct === null
                  ? "—"
                  : `${Math.round(Number(kpi.projecao.atingimento_projetado_pct))}%`}
              </Bloco>
              <Bloco rotulo="Gap para a meta">
                {formatarValor(kpi.projecao.gap, kpi.unidade)}
              </Bloco>
              <Bloco rotulo="Necessário por semana">
                {formatarValor(
                  kpi.projecao.necessario_por_semana,
                  kpi.unidade,
                )}
              </Bloco>
              <Bloco
                rotulo="Esforço vs ritmo atual"
                destaque={
                  kpi.projecao.alcancavel === false ? "text-red-700" : undefined
                }
              >
                {kpi.projecao.esforco_vs_ritmo === null
                  ? "—"
                  : `${Number(kpi.projecao.esforco_vs_ritmo).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}×`}
              </Bloco>
            </div>
            <p className="mt-3 text-xs text-slate-500">
              {frasePrjecao(
                kpi.tipo_acumulacao,
                kpi.projecao.esforco_vs_ritmo,
                kpi.projecao.alcancavel,
                kpi.projecao.semanas_restantes,
              )}
            </p>
          </section>
        )}

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          {/* Evolucao semanal */}
          <section className="rounded-lg border border-slate-200 bg-white p-5">
            <h3 className="text-sm font-semibold text-slate-800">
              Evolução semanal
            </h3>
            <p className="mb-4 text-xs text-slate-500">
              {kpi.tipo_acumulacao === "ACUMULA"
                ? "Barra = acumulado do mês; o traço marca a meta."
                : "Posição da taxa em cada semana; o traço marca a meta."}
            </p>

            {kpi.serie.length === 0 ? (
              <Vazio>Sem medições lançadas.</Vazio>
            ) : (
              <div className="space-y-2">
                {kpi.serie.map((p) => {
                  const v = Number(
                    kpi.tipo_acumulacao === "ACUMULA"
                      ? (p.valor_acumulado ?? 0)
                      : (p.valor ?? 0),
                  );
                  const largura = (Math.abs(v) / maxSerie) * 100;
                  const larguraMeta =
                    (Number(kpi.meta ?? 0) / maxSerie) * 100;
                  return (
                    <div key={p.semana} className="flex items-center gap-3">
                      <span className="w-6 shrink-0 text-xs text-slate-400">
                        S{p.semana}
                      </span>
                      <div className="relative h-7 flex-1 rounded bg-slate-100">
                        <div
                          className="h-full rounded bg-kami/80"
                          style={{ width: `${Math.min(largura, 100)}%` }}
                        />
                        {kpi.meta !== null && larguraMeta <= 100 && (
                          <div
                            className="absolute top-0 h-full w-0.5 bg-slate-700"
                            style={{ left: `${larguraMeta}%` }}
                            title="meta do mês"
                          />
                        )}
                      </div>
                      <span className="w-28 shrink-0 text-right text-xs tabular-nums text-slate-700">
                        {formatarValor(
                          kpi.tipo_acumulacao === "ACUMULA"
                            ? p.valor_acumulado
                            : p.valor,
                          kpi.unidade,
                        )}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {/* 3. Onde esta a quebra */}
          <section className="rounded-lg border border-slate-200 bg-white p-5">
            <h3 className="text-sm font-semibold text-slate-800">
              Abertura por regional
            </h3>
            <p className="mb-4 text-xs text-slate-500">
              A ação é definida sobre a regional fora do ritmo.
            </p>

            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                  <th className="py-2 text-left font-medium">Regional</th>
                  <th className="py-2 text-right font-medium">Realizado</th>
                  <th className="py-2 text-right font-medium">Meta</th>
                  <th className="py-2 text-right font-medium">Ating.</th>
                  <th className="py-2 text-right font-medium">Desvio</th>
                </tr>
              </thead>
              <tbody>
                {kpi.regionais.map((r) => {
                  const cor = coresSemaforo(r.semaforo);
                  return (
                    <tr
                      key={r.regional_codigo}
                      className="border-b border-slate-100 last:border-0"
                    >
                      <td className="py-2">
                        <span className="flex items-center gap-2">
                          <Pastilha semaforo={r.semaforo} />
                          <span className="font-medium text-slate-800">
                            {r.regional_codigo}
                          </span>
                        </span>
                      </td>
                      <td className="py-2 text-right tabular-nums text-slate-700">
                        {formatarValor(r.valor, kpi.unidade)}
                      </td>
                      <td className="py-2 text-right tabular-nums text-slate-400">
                        {formatarValor(r.meta, kpi.unidade)}
                      </td>
                      <td className="py-2 text-right tabular-nums text-slate-700">
                        {r.atingimento_pct === null
                          ? "—"
                          : `${Math.round(Number(r.atingimento_pct))}%`}
                      </td>
                      <td
                        className={`py-2 text-right font-medium tabular-nums ${cor.texto}`}
                      >
                        {formatarPP(r.desvio_pp)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </section>
        </div>

        {/* Quebras por categoria, quando existirem */}
        {Object.entries(porDimensao).map(([dimensao, itens]) => (
          <section
            key={dimensao}
            className="mt-6 rounded-lg border border-slate-200 bg-white p-5"
          >
            <h3 className="mb-4 text-sm font-semibold text-slate-800">
              {dimensao === "MOTIVO_PERDA"
                ? "Motivos das perdas"
                : dimensao === "FAIXA_COBERTURA"
                  ? "Composição do estoque por faixa de cobertura"
                  : dimensao}
            </h3>
            <BarrasCategoria itens={itens} />
          </section>
        ))}

        {nota && (
          <p className="mt-6 border-l-2 border-kami bg-slate-50 px-4 py-3 text-sm text-slate-700">
            {nota.texto}
          </p>
        )}
      </main>
    </>
  );
}

function Bloco({
  rotulo,
  children,
  destaque,
}: {
  rotulo: string;
  children: React.ReactNode;
  destaque?: string;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
      <dt className="text-xs text-slate-500">{rotulo}</dt>
      <dd
        className={`mt-1 text-lg font-semibold tabular-nums ${destaque ?? "text-slate-900"}`}
      >
        {children}
      </dd>
    </div>
  );
}

function BarrasCategoria({
  itens,
}: {
  itens: { categoria: string; valor: string; regional_codigo: string | null }[];
}) {
  const max = Math.max(...itens.map((i) => Number(i.valor)), 1);
  return (
    <div className="space-y-1.5">
      {itens.map((i, idx) => (
        <div key={`${i.categoria}-${i.regional_codigo ?? ""}-${idx}`} className="flex items-center gap-3">
          <span className="w-56 shrink-0 truncate text-xs text-slate-600">
            {i.regional_codigo ? `${i.regional_codigo} · ` : ""}
            {i.categoria}
          </span>
          <div className="h-5 flex-1 rounded bg-slate-100">
            <div
              className="h-full rounded bg-kami/70"
              style={{ width: `${(Number(i.valor) / max) * 100}%` }}
            />
          </div>
          <span className="w-12 shrink-0 text-right text-xs tabular-nums text-slate-700">
            {Number(i.valor).toLocaleString("pt-BR", {
              maximumFractionDigits: 0,
            })}
          </span>
        </div>
      ))}
    </div>
  );
}
