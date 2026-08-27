"use client";

import { Cabecalho } from "@/components/Cabecalho";
import { Carregando, Erro, Vazio } from "@/components/Estados";
import {
  buscarInadimplentes,
  buscarOcorrencias,
  buscarPainel,
} from "@/lib/api";
import { usePagina } from "@/lib/sessao";

const CAUSAS: Record<string, string> = {
  RUPTURA_ESTOQUE: "Ruptura de estoque",
  ATRASO_TRANSPORTE: "Atraso da transportadora",
  DIVERGENCIA_FISCAL: "Divergência fiscal",
  SEPARACAO_INCOMPLETA: "Separação incompleta",
  DIVERSOS: "Diversos",
};

const brl = (v: string) =>
  `R$ ${Number(v).toLocaleString("pt-BR", { maximumFractionDigits: 0 })} mil`;

export default function Detalhe() {
  const { usuario, dados, carregando, erro } = usePagina(async () => {
    const [painel, ocorrencias, titulos] = await Promise.all([
      buscarPainel(),
      buscarOcorrencias(),
      buscarInadimplentes(),
    ]);
    return { painel, ocorrencias, titulos };
  });

  if (carregando) return <Carregando texto="Carregando o detalhe…" />;
  if (erro) return <Erro mensagem={erro} />;
  if (!dados) return null;

  const { painel, ocorrencias, titulos } = dados;

  // Concentracao das causas de entrega, para nomear o problema estrutural.
  const porCausa = ocorrencias.reduce<Record<string, number>>((acc, o) => {
    acc[o.causa] = (acc[o.causa] ?? 0) + o.pedidos_afetados;
    return acc;
  }, {});
  const totalPedidos = Object.values(porCausa).reduce((a, b) => a + b, 0);
  const causaPrincipal = Object.entries(porCausa).sort((a, b) => b[1] - a[1])[0];

  const totalAberto = titulos.reduce((a, t) => a + Number(t.valor_aberto), 0);
  // Quantos clientes acumulam 80% do valor — a leitura de Pareto.
  const idx80 = titulos.findIndex((t) => Number(t.pct_acumulado) >= 80);
  const clientes80 = idx80 === -1 ? titulos.length : idx80 + 1;

  return (
    <>
      <Cabecalho ciclo={painel.ciclo} semana={painel.semana} usuario={usuario} />

      <main className="mx-auto max-w-[1600px] px-6 py-6">
        {/* Entregas com problema */}
        <section className="mb-10">
          <h2 className="text-base font-semibold text-slate-800">
            Entregas com problema · semana {painel.semana}
          </h2>
          <p className="mb-4 text-xs text-slate-500">
            {totalPedidos} pedidos afetados. Cliente, causa e plano de ação.
          </p>

          {ocorrencias.length === 0 ? (
            <Vazio>Nenhuma ocorrência registrada nesta semana.</Vazio>
          ) : (
            <>
              <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
                <table className="w-full min-w-[900px] text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                      <th className="px-4 py-2 text-left font-medium">Cliente</th>
                      <th className="px-3 py-2 text-left font-medium">Reg.</th>
                      <th className="px-3 py-2 text-left font-medium">Motivo</th>
                      <th className="px-3 py-2 text-right font-medium">Pedidos</th>
                      <th className="px-3 py-2 text-left font-medium">Plano de ação</th>
                      <th className="px-3 py-2 text-left font-medium">Responsável</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ocorrencias.map((o, i) => (
                      <tr
                        key={`${o.cliente_rotulo}-${i}`}
                        className="border-b border-slate-100 last:border-0"
                      >
                        <td className="px-4 py-2 font-medium text-slate-800">
                          {o.cliente_rotulo}
                        </td>
                        <td className="px-3 py-2 text-slate-600">
                          {o.regional_codigo ?? "—"}
                        </td>
                        <td className="px-3 py-2 text-slate-600">{o.motivo}</td>
                        <td className="px-3 py-2 text-right tabular-nums text-slate-800">
                          {o.pedidos_afetados}
                        </td>
                        <td className="px-3 py-2 text-slate-600">
                          {o.plano_acao ?? "—"}
                        </td>
                        <td className="px-3 py-2 text-slate-600">
                          {o.responsavel ?? "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {causaPrincipal && (
                <p className="mt-3 border-l-2 border-kami bg-slate-50 px-4 py-3 text-sm text-slate-700">
                  <strong>
                    {CAUSAS[causaPrincipal[0]] ?? causaPrincipal[0]}
                  </strong>{" "}
                  responde por {causaPrincipal[1]} dos {totalPedidos} pedidos (
                  {Math.round((causaPrincipal[1] / totalPedidos) * 100)}%) — é a
                  causa com maior concentração.
                </p>
              )}
            </>
          )}
        </section>

        {/* Inadimplencia por cliente */}
        <section>
          <h2 className="text-base font-semibold text-slate-800">
            Clientes inadimplentes
          </h2>
          <p className="mb-4 text-xs text-slate-500">
            {titulos.length} clientes, {brl(String(totalAberto))} em aberto.
            {clientes80 > 0 && (
              <>
                {" "}
                {clientes80} cliente{clientes80 > 1 ? "s" : ""} concentra
                {clientes80 > 1 ? "m" : ""} 80% do valor.
              </>
            )}
          </p>

          {titulos.length === 0 ? (
            <Vazio>Nenhum título em aberto registrado.</Vazio>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
              <table className="w-full min-w-[820px] text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                    <th className="px-4 py-2 text-right font-medium">#</th>
                    <th className="px-3 py-2 text-left font-medium">Cliente</th>
                    <th className="px-3 py-2 text-left font-medium">Reg.</th>
                    <th className="px-3 py-2 text-left font-medium">Consultor</th>
                    <th className="px-3 py-2 text-right font-medium">Em aberto</th>
                    <th className="px-3 py-2 text-right font-medium">Dias</th>
                    <th className="px-3 py-2 text-right font-medium">% acum.</th>
                    <th className="px-3 py-2 text-left font-medium">Situação</th>
                  </tr>
                </thead>
                <tbody>
                  {titulos.map((t) => (
                    <tr
                      key={t.posicao}
                      className={`border-b border-slate-100 last:border-0 ${
                        Number(t.pct_acumulado) <= 80 ? "bg-amber-50/40" : ""
                      }`}
                    >
                      <td className="px-4 py-2 text-right tabular-nums text-slate-400">
                        {t.posicao}
                      </td>
                      <td className="px-3 py-2 font-medium text-slate-800">
                        {t.cliente_rotulo}
                      </td>
                      <td className="px-3 py-2 text-slate-600">
                        {t.regional_codigo ?? "—"}
                      </td>
                      <td className="px-3 py-2 text-slate-600">
                        {t.consultor ?? "—"}
                      </td>
                      <td className="px-3 py-2 text-right font-medium tabular-nums text-slate-800">
                        {brl(t.valor_aberto)}
                      </td>
                      <td
                        className={`px-3 py-2 text-right tabular-nums ${
                          (t.dias_atraso ?? 0) > 60
                            ? "font-medium text-red-700"
                            : "text-slate-600"
                        }`}
                      >
                        {t.dias_atraso ?? "—"}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums text-slate-600">
                        {Math.round(Number(t.pct_acumulado))}%
                      </td>
                      <td className="px-3 py-2 text-xs text-slate-600">
                        {t.em_negociacao ? "em negociação" : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="mt-3 text-xs text-slate-400">
            As linhas destacadas compõem os 80% do valor em aberto — é onde a
            cobrança da semana deve se concentrar.
          </p>
        </section>
      </main>
    </>
  );
}
