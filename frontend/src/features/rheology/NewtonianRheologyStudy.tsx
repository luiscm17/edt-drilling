import { useState } from 'react';

type Reading = { rpm: number; dial: number; shear_rate_s_inv: number; shear_stress_pa: number };
type Result = {
  readings: Reading[];
  dynamic_viscosity: { quantity: string; value: number; unit: string };
  model_id: string; model_version: string; input_schema_version: string; result_schema_version: string;
  applicability: { status: string; assumptions: string; limitations: string };
};
type Draft = { id: number; rpm: string; dial: string };
const record = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null;
const nonnegative = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value) && value >= 0;
const positive = (value: unknown): value is number => nonnegative(value) && value > 0;
const display = (value: number) => value.toLocaleString('en-US', { maximumFractionDigits: 6 });

function validResult(value: unknown, count: number): value is Result {
  if (!record(value) || !record(value.dynamic_viscosity) || !record(value.applicability)) return false;
  return value.model_id === 'openoil.rheology.fann-newtonian' && value.model_version === '1.0.0'
    && value.input_schema_version === '1' && value.result_schema_version === '1'
    && value.dynamic_viscosity.quantity === 'dynamic_viscosity' && value.dynamic_viscosity.unit === 'Pa·s'
    && nonnegative(value.dynamic_viscosity.value)
    && Array.isArray(value.readings) && value.readings.length === count
    && value.readings.every((p: unknown) => record(p) && positive(p.rpm) && nonnegative(p.dial)
      && positive(p.shear_rate_s_inv) && nonnegative(p.shear_stress_pa))
    && new Set(value.readings.map((p: Reading) => p.rpm)).size === count
    && value.applicability.status === 'supported'
    && typeof value.applicability.assumptions === 'string' && value.applicability.assumptions.length > 0
    && typeof value.applicability.limitations === 'string' && value.applicability.limitations.length > 0;
}

export function NewtonianRheologyStudy() {
  const [readings, setReadings] = useState<Draft[]>([{ id: 1, rpm: '', dial: '' }]);
  const [nextId, setNextId] = useState(2);
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('Enter one or more Fann readings. Calculate only; no case is changed.');
  function invalidate() {
    setResult(null); setError(''); setStatus('Inputs changed. Calculate again; no case is changed.');
  }
  function edit(id: number, field: 'rpm' | 'dial', value: string) {
    setReadings(previous => previous.map(p => p.id === id ? { ...p, [field]: value } : p)); invalidate();
  }
  function add() {
    setReadings(previous => [...previous, { id: nextId, rpm: '', dial: '' }]);
    setNextId(id => id + 1); invalidate();
  }
  function remove(id: number) {
    setReadings(previous => previous.filter(p => p.id !== id)); invalidate();
  }
  async function calculate() {
    if (busy) return;
    setResult(null); setError(''); setStatus('No result is displayed.');
    const entries = readings.map(p => ({ rpm: Number(p.rpm), dial: Number(p.dial) }));
    if (readings.some(p => !p.rpm.trim() || !p.dial.trim())
      || entries.some(p => !positive(p.rpm) || !nonnegative(p.dial))) {
      setError('Enter positive finite RPM and nonnegative finite dial for every reading.'); return;
    }
    if (new Set(entries.map(p => p.rpm)).size !== entries.length) {
      setError('RPM readings must be unique.'); return;
    }
    setBusy(true); setStatus('Calculating Newtonian rheology…');
    try {
      const response = await fetch('/api/v1/rheology/newtonian/calculate', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ readings: entries }),
      });
      const body: unknown = await response.json().catch(() => { throw new Error(`Request failed (${response.status})`); });
      if (!response.ok) throw new Error(record(body) && typeof body.detail === 'string' ? body.detail : `Request failed (${response.status})`);
      if (!validResult(body, entries.length)) throw new Error('Invalid Newtonian rheology response');
      setResult(body); setStatus('Calculation complete. Not saved; hydraulic cases unchanged.');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Request failed');
      setStatus('Calculation failed. No result is displayed.');
    } finally { setBusy(false); }
  }
  return <section id="newtonian-rheology" tabIndex={-1} className="rheology-study panel" aria-labelledby="newtonian-heading">
    <div className="section-heading study-heading"><div><p className="eyebrow">10 / Newtonian · dynamic viscosity</p>
      <h2 id="newtonian-heading">Newtonian rheology study</h2></div><span className="study-badge">CALCULATE ONLY</span></div>
    <aside className="scope" aria-label="Newtonian rheology limitations">
      <strong>Assumed zero yield stress and constant viscosity: τ = μγ.</strong> One reading cannot establish Newtonian behavior.
      Multiple stress/rate ratios must agree within relative 1e-9 (absolute 0); this is numerical tolerance, not a noise fit.
      No WellPlan/vendor parity, field validation, hydraulic coupling or persistence.
    </aside>
    <div className="study-layout">
      <form noValidate onSubmit={event => { event.preventDefault(); void calculate(); }}>
        <fieldset className="editor" disabled={busy}><legend>Newtonian Fann readings</legend>
          <p className="hint" id="newtonian-hint">Unique positive RPM; nonnegative dimensionless dial. Zero dial gives zero viscosity.</p>
          {readings.map((p, index) => <fieldset className="geometry" key={p.id}><legend>Reading {index + 1}</legend>
            <label>Reading {index + 1} RPM<input type="number" step="any" min="0" required value={p.rpm}
              aria-describedby="newtonian-hint" aria-invalid={error ? true : undefined}
              onChange={event => edit(p.id, 'rpm', event.target.value)} /></label>
            <label>Reading {index + 1} dial<input type="number" step="any" min="0" required value={p.dial}
              aria-describedby="newtonian-hint" aria-invalid={error ? true : undefined}
              onChange={event => edit(p.id, 'dial', event.target.value)} /></label>
            <button type="button" className="text-button" disabled={readings.length === 1}
              onClick={() => remove(p.id)}>Remove reading {index + 1}</button>
          </fieldset>)}
          <button type="button" className="secondary" onClick={add}>Add reading</button>
          <div className="actions"><button className="primary" type="submit">Calculate Newtonian rheology</button></div>
        </fieldset>
      </form>
      <div aria-busy={busy}>
        <p role="status" className="status">{status}</p>{error && <p role="alert" className="error">{error}</p>}
        {result && <section aria-label="Newtonian result"><h3>Dynamic viscosity: {display(result.dynamic_viscosity.value)} Pa·s</h3>
          <table className="summary-table" aria-label="Newtonian shear data"><caption>Transformed observations · SI</caption>
            <thead><tr><th scope="col">RPM</th><th scope="col">Dial</th><th scope="col">Shear rate (s⁻¹)</th>
              <th scope="col">Observed stress (Pa)</th></tr></thead>
            <tbody>{result.readings.map(p => <tr key={p.rpm}><td>{display(p.rpm)}</td><td>{display(p.dial)}</td>
              <td>{display(p.shear_rate_s_inv)}</td><td>{display(p.shear_stress_pa)}</td></tr>)}</tbody>
          </table>
          <div className="provenance"><strong>{result.model_id} v{result.model_version}</strong>
            <p>Input schema {result.input_schema_version} · Result schema {result.result_schema_version}</p>
            <p>{result.applicability.assumptions}</p><p>{result.applicability.limitations}</p></div>
        </section>}
        <p className="result-note">γ = 1.70333 × RPM; τ = 0.01065 × dial × 47.88025898033584 Pa; μ = τ/γ (lowest RPM).
          Display rounding is not engineering accuracy. Independently validate before use.</p>
      </div>
    </div>
  </section>;
}
