"use client";

import { Cabecalho } from "@/components/Cabecalho";
import { Carregando, Erro, Vazio } from "@/components/Estados";
import { buscarCompromissos, buscarPainel } from "@/lib/api";
import { formatarData } from "@/lib/formato";
import { usePagina } from "@/lib/sessao";

const STATUS: Record<string, { rotulo: string; classe: string }> = {
  ABERTO: { rotulo: "Aberto", classe: "bg-slate-100 text-slate-700" },
  EM_ANDAMENTO: { rotulo: "Em andamento", classe: "bg-blue-50 text-blue-700" },
  CONCLUIDO: { rotulo: "Concluído", classe: "bg-emerald-50 text-emerald-700" },
  ATRASADO: { rotulo: "Atrasado", classe: "bg-red-50 text-red-700" },
  CANCELADO: { rotulo: "Cancelado", classe: "bg-slate-100 text-slate-500" },
};

export default function Compromissos() {
  const { usuario, dados, carregando, erro } = usePagina(async () => {
    const [painel, compromissos] = await Promise.all([
      buscarPainel(),
      buscarCompromissos(),
    ]);
    return { painel, compromissos };
  });

  if (carregando) return <Carregando texto="Carregando os compromissos…" />;
  if (erro) return <Erro mensagem={erro} />;
  if (!dados) return null;

  const { painel, compromissos } = dados;

  return (
    <>
      <Cabecalho ciclo={painel.ciclo} semana={painel.semana} usuario={usuario} />

      <main className="mx-auto max-w-[1400px] px-6 py-6">
        <h2 className="text-base font-semibold text-slate-800">
          Compromissos do ciclo
        </h2>
        <p className="mb-4 text-xs text-slate-500">
          Cada compromisso está ligado ao indicador que deve se mover — e volta
          ao painel na próxima reunião como resultado esperado.
        </p>

        {compromissos.length === 0 ? (
          <Vazio>Nenhum compromisso registrado neste ciclo.</Vazio>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
            <table className="w-full min-w-[900px] text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-4 py-2 text-left font-medium">Frente</th>
                  <th className="px-3 py-2 text-left font-medium">Ação</th>
                  <th className="px-3 py-2 text-left font-medium">Responsável</th>
                  <th className="px-3 py-2 text-left font-medium">Prazo</th>
                  <th className="px-3 py-2 text-left font-medium">Indicador</th>
                  <th className="px-3 py-2 text-left font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {compromissos.map((c) => {
                  const s = STATUS[c.status] ?? STATUS.ABERTO;
                  return (
                    <tr
                      key={c.id}
                      className="border-b border-slate-100 last:border-0"
                    >
                      <td className="px-4 py-2 font-medium text-slate-800">
                        {c.frente}
                      </td>
                      <td className="px-3 py-2 text-slate-600">{c.acao}</td>
                      <td className="px-3 py-2 text-slate-600">
                        {c.responsavel}
                      </td>
                      <td className="px-3 py-2 tabular-nums text-slate-600">
                        {formatarData(c.prazo)}
                      </td>
                      <td className="px-3 py-2 text-xs text-slate-500">
                        {c.indicador_codigo ?? "—"}
                      </td>
                      <td className="px-3 py-2">
                        <span
                          className={`inline-block rounded px-2 py-0.5 text-xs ${s.classe}`}
                        >
                          {s.rotulo}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </>
  );
}
