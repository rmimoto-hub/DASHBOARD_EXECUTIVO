"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { CartaoIndicador } from "@/components/CartaoIndicador";
import {
  ErroApi,
  buscarResumo,
  buscarUsuarioLogado,
  lerToken,
  limparToken,
  type ResumoIndicador,
  type Usuario,
} from "@/lib/api";

export default function Painel() {
  const router = useRouter();
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [itens, setItens] = useState<ResumoIndicador[]>([]);
  const [area, setArea] = useState<string>("");
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (!lerToken()) {
      router.replace("/login");
      return;
    }

    let cancelado = false;

    (async () => {
      try {
        const [u, resumo] = await Promise.all([
          buscarUsuarioLogado(),
          buscarResumo(),
        ]);
        if (cancelado) return;
        setUsuario(u);
        setItens(resumo);
      } catch (e) {
        if (cancelado) return;
        // Token expirado ou invalido: volta para o login.
        if (e instanceof ErroApi && e.status === 401) {
          limparToken();
          router.replace("/login");
          return;
        }
        setErro(e instanceof Error ? e.message : "Falha ao carregar o painel");
      } finally {
        if (!cancelado) setCarregando(false);
      }
    })();

    return () => {
      cancelado = true;
    };
  }, [router]);

  function sair() {
    limparToken();
    router.replace("/login");
  }

  const areas = Array.from(new Set(itens.map((i) => i.area))).sort();
  const visiveis = area ? itens.filter((i) => i.area === area) : itens;

  if (carregando) {
    return (
      <main className="grid min-h-screen place-items-center">
        <p className="text-slate-500">Carregando painel…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <header className="mb-8 flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <h1 className="text-2xl font-semibold text-kami">
            Painel de Gestao Executiva
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            {usuario ? `${usuario.nome} · ${usuario.perfil}` : ""}
          </p>
        </div>
        <button
          onClick={sair}
          className="rounded border border-slate-300 px-4 py-2 text-sm text-slate-700 transition hover:bg-slate-100"
        >
          Sair
        </button>
      </header>

      {erro && (
        <div
          role="alert"
          className="mb-6 rounded border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
        >
          {erro}
        </div>
      )}

      {areas.length > 0 && (
        <nav className="mb-6 flex flex-wrap gap-2">
          <FiltroArea rotulo="Todas" ativo={area === ""} onClick={() => setArea("")} />
          {areas.map((a) => (
            <FiltroArea
              key={a}
              rotulo={a}
              ativo={area === a}
              onClick={() => setArea(a)}
            />
          ))}
        </nav>
      )}

      {visiveis.length === 0 ? (
        <p className="rounded border border-dashed border-slate-300 px-4 py-12 text-center text-slate-500">
          Nenhum indicador cadastrado. Rode <code>make seed-fake</code> para
          carregar dados de teste.
        </p>
      ) : (
        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {visiveis.map((item) => (
            <CartaoIndicador key={item.codigo} item={item} />
          ))}
        </section>
      )}
    </main>
  );
}

function FiltroArea({
  rotulo,
  ativo,
  onClick,
}: {
  rotulo: string;
  ativo: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      aria-pressed={ativo}
      className={`rounded-full px-4 py-1.5 text-sm transition ${
        ativo
          ? "bg-kami text-white"
          : "border border-slate-300 text-slate-600 hover:bg-slate-100"
      }`}
    >
      {rotulo}
    </button>
  );
}
