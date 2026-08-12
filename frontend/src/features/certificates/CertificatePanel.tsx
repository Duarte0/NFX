import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../../shared/http";
import { Feedback } from "../../shared/ui/Feedback";
import { Badge, Button, Field, Panel } from "../../shared/ui/primitives";
import { getCertificate, uploadCertificate } from "./api";
import { Certificate } from "./types";
import { certificateStatusLabel } from "./CertificateInventoryPanel";

type CertificatePanelProps = {
  companyId: string;
  onChanged: () => Promise<void>;
  notify: (message: string) => void;
};

export function CertificatePanel({ companyId, onChanged, notify }: CertificatePanelProps) {
  const [certificate, setCertificate] = useState<Certificate | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(true);
  const [stale, setStale] = useState(false);
  const [error, setError] = useState("");
  const [uploadBusy, setUploadBusy] = useState(false);
  const certificateRequestSequence = useRef(0);
  const certificateRef = useRef<Certificate | null>(null);

  const loadCertificate = useCallback(async () => {
    const requestId = ++certificateRequestSequence.current;
    setLoading(true);
    setError("");
    try {
      const next = await getCertificate(companyId);
      if (requestId !== certificateRequestSequence.current) return;
      certificateRef.current = next.certificate;
      setCertificate(next.certificate);
      setStale(false);
    } catch {
      if (requestId !== certificateRequestSequence.current) return;
      setStale(certificateRef.current !== null);
      setError("Não foi possível consultar o certificado. A última leitura segura continua disponível.");
    } finally {
      if (requestId === certificateRequestSequence.current) setLoading(false);
    }
  }, [companyId]);

  useEffect(() => {
    void loadCertificate();
  }, [companyId, loadCertificate]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (uploadBusy) return;
    if (!file || !password) {
      notify("Selecione um arquivo .pfx e informe a senha.");
      return;
    }
    setUploadBusy(true);
    try {
      await uploadCertificate(companyId, file, password);
      setPassword("");
      setFile(null);
      notify("Certificado validado e armazenado com segurança.");
      await loadCertificate();
      await onChanged();
    } catch (caught: unknown) {
      setPassword("");
      setFile(null);
      notify(caught instanceof ApiError ? caught.detail : "Não foi possível cadastrar o certificado.");
    } finally {
      setUploadBusy(false);
    }
  }

  return (
    <Panel as="section" title="Certificado A1" className="certificate-panel">
      {loading && <Feedback state="loading" message="Consultando o certificado…" />}
      {stale && (
        <div className="feature-stale" role="status">
          <Badge variant="warning">Leitura desatualizada</Badge>
          <span>A última leitura segura permanece visível.</span>
        </div>
      )}
      {error && <Feedback state="unavailable" message={error} />}
      {!loading && !error && certificate ? (
        <div className="certificate-current">
          <Badge variant={certificate.status === "valido" ? "success" : certificate.status === "proximo_vencimento" ? "warning" : "danger"}>
            {certificateStatusLabel(certificate.status)}
          </Badge>
          <p>Validade: {certificate.not_before} até {certificate.not_after}</p>
          <p>{certificate.days_until_expiry === null ? "Prazo não informado" : `${certificate.days_until_expiry} dia(s) restantes`}</p>
        </div>
      ) : !loading && !error ? (
        <Feedback state="empty" message="Nenhum certificado corrente está associado a esta empresa." />
      ) : null}
      <form onSubmit={submit} className="feature-form">
        <Field id={`certificate-file-${companyId}`} label="Arquivo .pfx" hint="O material não é exibido nem persistido no navegador.">
          <input
            type="file"
            accept=".pfx,application/x-pkcs12"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            required
          />
        </Field>
        <Field id={`certificate-password-${companyId}`} label="Senha do certificado" hint="A senha é enviada somente ao owner autorizado.">
          <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
        </Field>
        <Button type="submit" disabled={uploadBusy}>{uploadBusy ? "Validando…" : "Validar e substituir"}</Button>
      </form>
    </Panel>
  );
}
