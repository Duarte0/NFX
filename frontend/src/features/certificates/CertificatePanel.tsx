import { FormEvent, useCallback, useEffect, useState } from "react";
import { ApiError } from "../../shared/http";
import { getCertificate, uploadCertificate } from "./api";
import { Certificate } from "./types";

type CertificatePanelProps = {
  companyId: string;
  onChanged: () => Promise<void>;
  notify: (message: string) => void;
};

export function CertificatePanel({ companyId, onChanged, notify }: CertificatePanelProps) {
  const [certificate, setCertificate] = useState<Certificate | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [password, setPassword] = useState("");

  const loadCertificate = useCallback(async () => {
    try {
      setCertificate((await getCertificate(companyId)).certificate);
    } catch {
      setCertificate(null);
    }
  }, [companyId]);

  useEffect(() => {
    void loadCertificate();
  }, [companyId, loadCertificate]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || !password) {
      notify("Selecione um arquivo .pfx e informe a senha.");
      return;
    }
    try {
      await uploadCertificate(companyId, file, password);
      setPassword("");
      setFile(null);
      notify("Certificado validado e armazenado com segurança.");
      await loadCertificate();
      await onChanged();
    } catch (error: unknown) {
      setPassword("");
      setFile(null);
      notify(error instanceof ApiError ? error.detail : "Não foi possível cadastrar o certificado.");
    }
  }

  return (
    <>
      {certificate ? <p>Certificado: {certificate.status}</p> : <p>Nenhum certificado corrente.</p>}
      <form onSubmit={submit}>
        <label>
          Arquivo .pfx
          <input
            type="file"
            accept=".pfx,application/x-pkcs12"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            required
          />
        </label>
        <label>
          Senha do certificado
          <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
        </label>
        <button type="submit">Validar e substituir</button>
      </form>
    </>
  );
}
