"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { guardarToken, login } from "@/lib/api";

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      guardarToken(await login(email, senha));
      router.replace("/");
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Nao foi possivel entrar");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center px-6">
      <form
        onSubmit={enviar}
        className="w-full max-w-sm rounded-lg border border-slate-200 bg-white p-8 shadow-sm"
      >
        <h1 className="text-xl font-semibold text-kami">dir-dashboard</h1>
        <p className="mt-1 text-sm text-slate-500">
          Painel de Gestao Executiva — KAMI CO.
        </p>

        <label className="mt-6 block text-sm font-medium text-slate-700">
          E-mail
          <input
            type="email"
            required
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-slate-900 outline-none focus:border-kami focus:ring-1 focus:ring-kami"
          />
        </label>

        <label className="mt-4 block text-sm font-medium text-slate-700">
          Senha
          <input
            type="password"
            required
            autoComplete="current-password"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-slate-900 outline-none focus:border-kami focus:ring-1 focus:ring-kami"
          />
        </label>

        {erro && (
          <p role="alert" className="mt-4 text-sm text-red-600">
            {erro}
          </p>
        )}

        <button
          type="submit"
          disabled={enviando}
          className="mt-6 w-full rounded bg-kami px-4 py-2.5 font-medium text-white transition hover:bg-kami-claro disabled:opacity-60"
        >
          {enviando ? "Entrando…" : "Entrar"}
        </button>
      </form>
    </main>
  );
}
