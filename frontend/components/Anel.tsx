import { coresSemaforo } from "@/lib/formato";
import type { Semaforo } from "@/lib/api";

/**
 * Anel de atingimento — o sinalizador circular do comite.
 *
 * O arco mostra o % atingido; o tracinho externo marca o ritmo esperado
 * da semana. A cor compara os dois, nao o atingimento com 100%.
 */
export function Anel({
  atingimento,
  esperado,
  semaforo,
  tamanho = 88,
}: {
  atingimento: number | null;
  esperado: number;
  semaforo: Semaforo;
  tamanho?: number;
}) {
  const raio = tamanho / 2 - 7;
  const circ = 2 * Math.PI * raio;
  const pct = Math.max(0, Math.min(atingimento ?? 0, 150));
  const preenchido = (Math.min(pct, 100) / 100) * circ;
  const cor = coresSemaforo(semaforo);

  const traco =
    semaforo === "VERDE"
      ? "#10b981"
      : semaforo === "AMBAR"
        ? "#f59e0b"
        : semaforo === "VERMELHO"
          ? "#ef4444"
          : "#cbd5e1";

  // Angulo do marcador de ritmo esperado, comecando no topo.
  const anguloEsperado = (Math.min(esperado, 100) / 100) * 360 - 90;

  return (
    <div
      className="relative shrink-0"
      style={{ width: tamanho, height: tamanho }}
    >
      <svg width={tamanho} height={tamanho} className="-rotate-90">
        <circle
          cx={tamanho / 2}
          cy={tamanho / 2}
          r={raio}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth="7"
        />
        <circle
          cx={tamanho / 2}
          cy={tamanho / 2}
          r={raio}
          fill="none"
          stroke={traco}
          strokeWidth="7"
          strokeLinecap="round"
          strokeDasharray={`${preenchido} ${circ}`}
        />
      </svg>

      {/* Marcador do ritmo esperado */}
      <svg
        width={tamanho}
        height={tamanho}
        className="pointer-events-none absolute inset-0"
      >
        <line
          x1={tamanho / 2 + (raio - 6) * Math.cos((anguloEsperado * Math.PI) / 180)}
          y1={tamanho / 2 + (raio - 6) * Math.sin((anguloEsperado * Math.PI) / 180)}
          x2={tamanho / 2 + (raio + 6) * Math.cos((anguloEsperado * Math.PI) / 180)}
          y2={tamanho / 2 + (raio + 6) * Math.sin((anguloEsperado * Math.PI) / 180)}
          stroke="#334155"
          strokeWidth="2"
          strokeLinecap="round"
        />
      </svg>

      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-xl font-semibold tabular-nums ${cor.texto}`}>
          {atingimento === null ? "—" : Math.round(atingimento)}
          {atingimento !== null && <span className="text-sm">%</span>}
        </span>
        <span className="text-[10px] text-slate-400">da meta</span>
      </div>
    </div>
  );
}
