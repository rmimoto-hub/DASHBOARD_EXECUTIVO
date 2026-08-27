"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import {
  ErroApi,
  buscarUsuarioLogado,
  lerToken,
  limparToken,
  type Usuario,
} from "@/lib/api";

/**
 * Carrega os dados de uma pagina protegida.
 *
 * Reune o que todas as telas repetem: exigir token, buscar o usuario,
 * derrubar a sessao quando a API responde 401 e expor erro e carregamento.
 */
export function usePagina<T>(carregar: () => Promise<T>, deps: unknown[] = []) {
  const router = useRouter();
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [dados, setDados] = useState<T | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (!lerToken()) {
      router.replace("/login");
      return;
    }

    let cancelado = false;
    setCarregando(true);

    (async () => {
      try {
        const [u, d] = await Promise.all([buscarUsuarioLogado(), carregar()]);
        if (cancelado) return;
        setUsuario(u);
        setDados(d);
        setErro(null);
      } catch (e) {
        if (cancelado) return;
        if (e instanceof ErroApi && e.status === 401) {
          limparToken();
          router.replace("/login");
          return;
        }
        setErro(e instanceof Error ? e.message : "Falha ao carregar");
      } finally {
        if (!cancelado) setCarregando(false);
      }
    })();

    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router, ...deps]);

  return { usuario, dados, carregando, erro };
}
