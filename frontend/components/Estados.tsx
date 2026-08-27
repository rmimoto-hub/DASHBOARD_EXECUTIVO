export function Carregando({ texto = "Carregando…" }: { texto?: string }) {
  return (
    <div className="grid min-h-[50vh] place-items-center">
      <p className="text-slate-500">{texto}</p>
    </div>
  );
}

export function Erro({ mensagem }: { mensagem: string }) {
  return (
    <div
      role="alert"
      className="mx-auto mt-8 max-w-2xl rounded border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
    >
      {mensagem}
    </div>
  );
}

export function Vazio({ children }: { children: React.ReactNode }) {
  return (
    <p className="rounded border border-dashed border-slate-300 px-4 py-10 text-center text-sm text-slate-500">
      {children}
    </p>
  );
}
