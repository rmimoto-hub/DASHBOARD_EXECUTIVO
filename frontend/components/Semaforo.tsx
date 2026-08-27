import type { Semaforo as TipoSemaforo } from "@/lib/api";
import { coresSemaforo } from "@/lib/formato";

/** Pastilha circular do semaforo, com rotulo opcional. */
export function Pastilha({
  semaforo,
  comRotulo = false,
}: {
  semaforo: TipoSemaforo;
  comRotulo?: boolean;
}) {
  const c = coresSemaforo(semaforo);
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className={`inline-block h-2.5 w-2.5 shrink-0 rounded-full ${c.pastilha}`}
        aria-hidden="true"
      />
      <span className={comRotulo ? `text-xs ${c.texto}` : "sr-only"}>
        {c.rotulo}
      </span>
    </span>
  );
}
