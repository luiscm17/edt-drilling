import { useState } from 'react';

type Boundary = 'pipe' | 'annulus';
type Result = {
  power: { quantity: 'hydraulic_power'; value: number; unit: 'hp' };
  pressure_boundary: Boundary;
  model_id: string; model_version: string; input_schema_version: string; result_schema_version: string;
  applicability: { status: string; assumptions: string; limitations: string };
};
function validResult(value: unknown, boundary: Boundary): value is Result {
  if (!value || typeof value !== 'object') return false;
  const body = value as Partial<Result>;
  return body.power?.quantity === 'hydraulic_power' && body.power.unit === 'hp'
    && Number.isFinite(body.power.value) && body.power.value > 0
    && body.pressure_boundary === boundary
    && body.model_id === 'openoil.hydraulics.documented-pressure-loss-power'
    && body.model_version === '1.0.0' && body.input_schema_version === '1' && body.result_schema_version === '1'
    && body.applicability?.status === 'supported'
    && typeof body.applicability.assumptions === 'string' && body.applicability.assumptions.length > 0
    && typeof body.applicability.limitations === 'string' && body.applicability.limitations.length > 0;
}
export function BitHydraulicPowerStudy() {
  const [flow, setFlow] = useState('');
  const [pressure, setPressure] = useState('');
  const [boundary, setBoundary] = useState<Boundary>('pipe');
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('Supply a pipe or annulus pressure loss and circulation rate. Calculate only.');
  function invalidate() { setResult(null); setError(''); setStatus('Inputs changed. Calculate again; saved cases unchanged.'); }
  async function calculate() {
    setResult(null); setError('');
    if (!flow.trim() || !pressure.trim() || !Number.isFinite(Number(flow)) || Number(flow) <= 0
      || !Number.isFinite(Number(pressure)) || Number(pressure) <= 0) {
      setError('Enter positive finite flow and pressure loss in SI units.'); setStatus('Invalid inputs. No result.'); return;
    }
    setBusy(true); setStatus('Calculating hydraulic power…');
    try {
      const response = await fetch('/api/v1/bit-hydraulic-power/calculate', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ flow_m3_s: Number(flow), pressure_loss_pa: Number(pressure), pressure_boundary: boundary }),
      });
      const body: unknown = await response.json().catch(() => { throw new Error(`Request failed (${response.status})`); });
      if (!response.ok) {
        const detail = body && typeof body === 'object' && 'detail' in body ? body.detail : undefined;
        throw new Error(typeof detail === 'string' ? detail : `Request failed (${response.status})`);
      }
      if (!validResult(body, boundary)) throw new Error('Invalid hydraulic power response');
      setResult(body); setStatus('Calculation complete. Not saved; hydraulic cases unchanged.');
    } catch (reason) {
      setResult(null); setError(reason instanceof Error ? reason.message : 'Request failed');
      setStatus('Calculation failed. No result.');
    } finally { setBusy(false); }
  }
  return <section id="bit-hydraulic-power" tabIndex={-1} className="nozzle-study panel" aria-labelledby="power-heading">
    <div className="section-heading study-heading"><div><p className="eyebrow">12 / Supplied pressure-loss power</p>
      <h2 id="power-heading">Hydraulic power study</h2></div><span className="study-badge">CALCULATE ONLY</span></div>
    <aside className="scope" aria-label="Hydraulic power limitations">
      <strong>User-supplied pipe or annulus loss, not bit/nozzle pressure loss.</strong> This standalone calculation does not
      calculate a pressure profile, optimize nozzles, or validate source pressure. No vendor parity or field validation.
    </aside>
    <div className="study-layout"><form noValidate onSubmit={event => { event.preventDefault(); void calculate(); }}>
      <fieldset className="editor" disabled={busy}><legend className="sr-only">Hydraulic power inputs</legend>
        <div className="fluid-grid"><label>Circulation rate (m³/s)
          <input type="number" step="any" value={flow} onChange={event => { setFlow(event.target.value); invalidate(); }} /></label>
          <label>Supplied pressure loss (Pa)
            <input type="number" step="any" value={pressure} onChange={event => { setPressure(event.target.value); invalidate(); }} /></label>
          <label>Pressure-loss passage<select value={boundary} onChange={event => { setBoundary(event.target.value as Boundary); invalidate(); }}>
            <option value="pipe">Pipe</option><option value="annulus">Annulus</option></select></label></div>
        <div className="actions"><button className="primary" type="submit">Calculate hydraulic power</button></div>
      </fieldset>
    </form><div aria-busy={busy}><h3>Pressure-loss hydraulic power / hp</h3>
      <p className="status" role="status">{status}</p>{error && <p className="error" role="alert">{error}</p>}
      {result ? <><table className="summary-table" aria-label="Hydraulic power result"><thead><tr><th>Passage</th><th>Power</th><th>Unit</th></tr></thead>
        <tbody><tr><td>{result.pressure_boundary}</td><td>{result.power.value.toLocaleString('en-US', { maximumFractionDigits: 6 })}</td><td>{result.power.unit}</td></tr></tbody></table>
        <div className="provenance"><strong>{result.model_id}</strong><p>Model version {result.model_version} · Input schema {result.input_schema_version} · Result schema {result.result_schema_version}</p>
          <p>{result.applicability.assumptions}</p><p>{result.applicability.limitations}</p></div></> : <p className="study-empty">NO POWER RESULT / Awaiting calculation</p>}
      <p className="result-note">Documented API relation: power (hp) = Q (US gpm) × supplied passage pressure loss (psi) / 1714. SI inputs are converted to API units before applying the literal divisor. Display rounding is not engineering accuracy. No saved case changes.</p>
    </div></div>
  </section>;
}
