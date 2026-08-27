"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import type { Ciclo, Usuario } from "@/lib/api";
import { limparToken } from "@/lib/api";
import { formatarData, nomeMes } from "@/lib/formato";

const ABAS = [
  { href: "/", rotulo: "Painel" },
  { href: "/matriz", rotulo: "Onde está a quebra" },
  { href: "/detalhe", rotulo: "Detalhe" },
  { href: "/compromissos", rotulo: "Compromissos" },
];

export function Cabecalho({
  ciclo,
  semana,
  usuario,
}: {
  ciclo: Ciclo | null;
  semana: number | null;
  usuario: Usuario | null;
}) {
  const router = useRouter();
  const caminho = usePathname();

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-4 px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold text-kami">
            Comitê Executivo Semanal
          </h1>
          {ciclo && semana && (
            <p className="mt-0.5 text-sm text-slate-500">
              {nomeMes(ciclo.mes)} de {ciclo.ano} · semana {semana} de{" "}
              {ciclo.semanas_total} · fechamento em{" "}
              {formatarData(ciclo.data_fechamento)}
            </p>
          )}
        </div>

        <div className="flex items-center gap-4">
          {usuario && (
            <span className="text-xs text-slate-500">
              {usuario.nome} · {usuario.perfil}
            </span>
          )}
          <button
            onClick={() => {
              limparToken();
              router.replace("/login");
            }}
            className="rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-700 transition hover:bg-slate-100"
          >
            Sair
          </button>
        </div>
      </div>

      <nav className="mx-auto max-w-[1600px] px-6">
        <ul className="flex gap-1">
          {ABAS.map((aba) => {
            const ativo =
              aba.href === "/" ? caminho === "/" : caminho.startsWith(aba.href);
            return (
              <li key={aba.href}>
                <Link
                  href={aba.href}
                  aria-current={ativo ? "page" : undefined}
                  className={`inline-block border-b-2 px-3 py-2 text-sm transition ${
                    ativo
                      ? "border-kami font-medium text-kami"
                      : "border-transparent text-slate-500 hover:text-slate-800"
                  }`}
                >
                  {aba.rotulo}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </header>
  );
}
