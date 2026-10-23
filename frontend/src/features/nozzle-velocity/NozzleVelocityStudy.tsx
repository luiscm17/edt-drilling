import { useState } from 'react';

const fields = [
  ['flow_m3_s', 'Nozzle flow (m³/s)'], ['total_nozzle_area_m2', 'Total nozzle flow area (m²)'],
] as const;

export function NozzleVelocityStudy() {
  const [inputs, setInputs] = useState({ flow_m3_s: '', total_nozzle_area_m2: '' });
  const [velocity, setVelocity] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('Enter flow and total area. Calculate-only; no saved case is changed.');
  function edit(key: keyof typeof inputs, value: string) {
    setInputs(previous => ({ ...previous, [key]: value }));
    setVelocity(null); setError('');
    setStatus('Nozzle inputs changed. Calculate again; no saved case is changed.');
  }
  async function calculate() {
    setVelocity(null); setError('');
    const flow = Number(inputs.flow_m3_s), area = Number(inputs.total_nozzle_area_m2);
    if (!Number.isFinite(flow) || flow <= 0 || !Number.isFinite(area) || area <= 0) {
      setError('Enter positive finite flow and total nozzle area in SI units.');
      setStatus('Invalid inputs. No result is displayed.');
      return;
    }
    setBusy(true); setStatus('Calculating nozzle velocity…');
    try {
      const response = await fetch('/api/v1/nozzle-velocity/calculate', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ flow_m3_s: flow, total_nozzle_area_m2: area }),
      });
      const body = await response.json().catch(() => { throw new Error(`Request failed (${response.status})`); });
      if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : `Request failed (${response.status})`);
      if (typeof body.velocity_m_s !== 'number' || !Number.isFinite(body.velocity_m_s) || body.velocity_m_s <= 0) {
        throw new Error('Invalid nozzle velocity response');
      }
      setVelocity(body.velocity_m_s);
      setStatus('Calculation complete. Not saved; hydraulic ledger unchanged.');
    } catch (reason) {
      setVelocity(null); setError(reason instanceof Error ? reason.message : 'Request failed');
      setStatus('Calculation failed. No result is displayed; hydraulic ledger unchanged.');
    } finally { setBusy(false); }
  }
  return <section id="nozzle-velocity" tabIndex={-1} className="nozzle-study panel" aria-labelledby="nozzle-heading">
    <div className="section-heading study-heading"><div><p className="eyebrow">03 / Documented equation study</p>
      <h2 id="nozzle-heading">Nozzle velocity study</h2></div><span className="study-badge">NOZZLE / CALCULATE ONLY</span></div>
    <aside className="scope" aria-label="Nozzle velocity limitations">
      <strong>Velocity at entered flow and area — not an operating limit or optimizer.</strong>
      Independent implementation of an installed-help equation. No executed vendor numerical parity claimed.
      No pressure-loss prediction, coupled hydraulics, erosion or transient/multiphase model. Not validated for field decisions.
    </aside>
    <div className="study-layout">
      <form noValidate onSubmit={event => { event.preventDefault(); void calculate(); }}>
        <fieldset className="editor" disabled={busy}>
          <legend className="sr-only">Nozzle velocity inputs</legend>
          <p className="hint" id="nozzle-input-hint">Positive finite SI quantities only. Total flow area is the sum of all nozzle areas, not a diameter or one nozzle's area.</p>
          <div className="fluid-grid nozzle-fields">{fields.map(([key, label]) => <label key={key}>{label}
            <input type="number" step="any" min="0" required value={inputs[key]} aria-describedby="nozzle-input-hint"
              aria-invalid={error && !busy ? true : undefined} onChange={event => edit(key, event.target.value)} />
          </label>)}</div>
          <div className="actions"><button className="primary" type="submit">Calculate nozzle velocity</button></div>
        </fieldset>
      </form>
      <div aria-busy={busy}>
        <h3>Nozzle velocity / SI</h3>
        <p className="status" role="status">{status}</p>
        {error && <p className="error" role="alert">{error}</p>}
        {velocity !== null ? <table className="summary-table" aria-label="Nozzle velocity SI result">
          <thead><tr><th scope="col">Quantity</th><th scope="col">Value</th><th scope="col">Unit</th></tr></thead>
          <tbody><tr><th scope="row">Nozzle velocity</th><td>{velocity.toLocaleString('en-US', { maximumFractionDigits: 4 })}</td><td>m/s</td></tr></tbody>
        </table> : <p className="study-empty">NO NOZZLE RESULT / Awaiting a successful calculation</p>}
        <div className="provenance nozzle-formula">
          <strong>Documented formula / fixed coefficient</strong>
          <p>v (ft/s) = 0.95 × Q (US gpm) / (2.96 × A (in²)). The backend converts SI inputs to these units and converts velocity back to m/s.</p>
          <p>Retaining the installed help's literal 2.96 is a documentation-fidelity choice, not calibration.
            Exact unit conversion implies approximately 3.116883117 instead; this equation is about 5.30% higher than 0.95 × Q / A in coherent SI. The approximation's meaning/precision remains unverified.</p>
        </div>
        <p className="result-note">Temporary result; no save action or hydraulic snapshot changes. Display rounds to at most four decimals;
          small values can round to zero. Digits are not accuracy. Independently validate before engineering use.</p>
      </div>
    </div>
  </section>;
}
