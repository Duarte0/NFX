import { useCallback, useEffect, useState } from "react";
import { Feedback } from "../../shared/ui/Feedback";
import { listAuditEvents } from "./api";
import { AuditEvent } from "./types";

type AuditSectionProps = { loadSignal: number; notify: (message: string) => void };

export function AuditSection({ loadSignal, notify }: AuditSectionProps) {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [error, setError] = useState("");

  const loadAudit = useCallback(async () => {
    try {
      setError("");
      setEvents((await listAuditEvents()).events);
    } catch {
      setError("Não foi possível consultar a auditoria.");
      notify("Não foi possível consultar a auditoria.");
    }
  }, [notify]);

  useEffect(() => {
    if (loadSignal > 0) void loadAudit();
  }, [loadAudit, loadSignal]);

  return (
    <section id="auditoria">
      <h2>Auditoria</h2>
      <button onClick={() => void loadAudit()}>Atualizar auditoria</button>
      <Feedback message={error} error />
      <table>
        <thead>
          <tr><th>Data/hora</th><th>Ação</th><th>Entidade</th><th>Resultado</th><th>Motivo</th></tr>
        </thead>
        <tbody>
          {events.map((item) => (
            <tr key={item.id}>
              <td>{item.occurred_at}</td>
              <td>{item.action}</td>
              <td>{item.entity_type} · {item.entity_id}</td>
              <td>{item.result}</td>
              <td>{item.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
