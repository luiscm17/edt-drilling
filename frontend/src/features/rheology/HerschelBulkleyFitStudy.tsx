import { useState } from 'react';

type Parameter = { value: number; unit: string };
type Point = { rpm: number; dial: number; shear_rate_s_inv: number; shear_stress_pa: number; predicted_stress_pa: number; residual_pa: number };
type Diagnostics = {
  objective: string; sse_pa2: number; rmse_pa: number; max_abs_residual_pa: number;
  evaluations: number; n_min: number; n_max: number; n_step: number;
  near_optimal_n_min: number; near_optimal_n_max: number; near_optimal_count: number; at_n_bound: boolean; warning: string;
};
type Result = {
  parameters: Record<string, Parameter>; points: Point[]; diagnostics: Diagnostics;
  model_id: string; model_version: string; input_schema_version: string; result_schema_version: string;
  applicability: { status: string; assumptions: string; limitations: string };
};
type Draft = { id: number; rpm: string; dial: string };
const record = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null;
const finite = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
const nonnegative = (v: unknown): v is number => finite(v) && v >= 0;
const positive = (v: unknown): v is number => nonnegative(v) && v > 0;
const text = (v: unknown): v is string => typeof v === 'string' && v.length > 0;
const display = (v: number) => v.toLocaleString('en-US', { maximumSignificantDigits: 6 });
function validResult(v: unknown, count: number): v is Result {
  if (!record(v) || !record(v.parameters) || !record(v.diagnostics) || !record(v.applicability)) return false;
  const p = v.parameters, d = v.diagnostics;
  return v.model_id === 'openoil.rheology.fann-herschel-bulkley-fit' && v.model_version === '1.0.0'
    && v.input_schema_version === '1' && v.result_schema_version === '1'
    && [['yield_stress_pa', 'Pa'], ['consistency_index_pa_s_n', 'Pa·s^n'], ['flow_behavior_index', '1']].every(([key, unit]) => {
      const value = p[key]; return record(value) && nonnegative(value.value) && value.unit === unit;
    }) && record(p.flow_behavior_index) && positive(p.flow_behavior_index.value)
    && Array.isArray(v.points) && v.points.length === count && v.points.every((point: unknown) => record(point)
      && positive(point.rpm) && nonnegative(point.dial) && positive(point.shear_rate_s_inv)
      && nonnegative(point.shear_stress_pa) && nonnegative(point.predicted_stress_pa) && finite(point.residual_pa))
    && new Set(v.points.map((point: Point) => point.rpm)).size === count
    && d.objective === 'unweighted stress least squares; discrete n grid'
    && ['sse_pa2', 'rmse_pa', 'max_abs_residual_pa'].every(key => nonnegative(d[key]))
    && d.evaluations === 391 && d.n_min === 0.05 && d.n_max === 2 && d.n_step === 0.005
    && finite(d.near_optimal_n_min) && finite(d.near_optimal_n_max)
    && d.near_optimal_n_min >= 0.05 && d.near_optimal_n_max <= 2 && d.near_optimal_n_min <= d.near_optimal_n_max
    && finite(d.near_optimal_count) && Number.isInteger(d.near_optimal_count) && d.near_optimal_count >= 1 && d.near_optimal_count <= 391
    && typeof d.at_n_bound === 'boolean' && text(d.warning)
    && v.applicability.status === 'supported' && text(v.applicability.assumptions) && text(v.applicability.limitations);
}

export function HerschelBulkleyFitStudy() {
  const [readings, setReadings] = useState<Draft[]>([1, 2, 3].map(id => ({ id, rpm: '', dial: '' })));
  const [nextId, setNextId] = useState(4);
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('Enter at least three distinct Fann readings. No case is changed.');
  function invalidate() { setResult(null); setError(''); setStatus('Inputs changed. Fit again.'); }
  function edit(id: number, field: 'rpm' | 'dial', value: string) {
    setReadings(previous => previous.map(p => p.id === id ? { ...p, [field]: value } : p)); invalidate();
  }
  function add() {
    setReadings(previous => [...previous, { id: nextId, rpm: '', dial: '' }]); setNextId(id => id+1); invalidate();
  }
  async function calculate() {
    if (busy) return;
    setResult(null); setError(''); setStatus('No result is displayed.');
    const entries = readings.map(p => ({ rpm: Number(p.rpm), dial: Number(p.dial) }));
    if (readings.some(p => !p.rpm.trim() || !p.dial.trim()) || entries.some(p => !positive(p.rpm) || !nonnegative(p.dial))) {
      setError('Enter positive finite RPM and nonnegative finite dial for every reading.'); return;
    }
    if (new Set(entries.map(p => p.rpm)).size !== entries.length) { setError('RPM readings must be unique.'); return; }
    setBusy(true); setStatus('Fitting conventional HB…');
    try {
      const response = await fetch('/api/v1/rheology/herschel-bulkley-fit/calculate', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ readings: entries }),
      });
      const body: unknown = await response.json().catch(() => { throw new Error(`Request failed (${response.status})`); });
      if (!response.ok) throw new Error(record(body) && text(body.detail) ? body.detail : `Request failed (${response.status})`);
      if (!validResult(body, entries.length)) throw new Error('Invalid conventional HB fit response');
      setResult(body); setStatus('Fit complete. Not saved; hydraulic cases unchanged.');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Request failed'); setStatus('Fit failed. No result is displayed.');
    } finally { setBusy(false); }
  }
  return <section id="herschel-bulkley-fit" tabIndex={-1} className="rheology-study panel" aria-labelledby="hb-fit-heading">
    <div className="section-heading study-heading"><div><p className="eyebrow">11 / Conventional HB · bounded fit</p>
      <h2 id="hb-fit-heading">Conventional HB fit study</h2></div><span className="study-badge">CALCULATE ONLY</span></div>
    <aside className="scope" aria-label="HB fit limitations"><strong>τ = τ₀ + Kγⁿ; unweighted stress least squares.</strong>
      {' '}Nonnegative τ₀ and K; n searched only from 0.05 to 2 in steps of 0.005 (391 complete profiles).
      Finite-grid selection does not establish unique parameters. No WellPlan/vendor parity, generalized-HB fitting, hydraulic coupling or field validation.
    </aside>
    <div className="study-layout"><form noValidate onSubmit={event => { event.preventDefault(); void calculate(); }}>
      <fieldset className="editor" disabled={busy}><legend>Conventional HB Fann readings</legend>
        <p id="hb-fit-hint" className="hint">3–1000 distinct positive RPM; nonnegative dial. γ = 1.70333 × RPM;
          τ = 0.01065 × 47.88025898033584 × dial Pa. Constant/decreasing or numerically degenerate data may be rejected.</p>
        {readings.map((p, index) => <fieldset className="geometry" key={p.id}><legend>HB reading {index+1}</legend>
          <label>HB reading {index+1} RPM<input type="number" step="any" required value={p.rpm}
            aria-describedby="hb-fit-hint" aria-invalid={error ? true : undefined} onChange={event => edit(p.id, 'rpm', event.target.value)} /></label>
          <label>HB reading {index+1} dial<input type="number" step="any" required value={p.dial}
            aria-describedby="hb-fit-hint" aria-invalid={error ? true : undefined} onChange={event => edit(p.id, 'dial', event.target.value)} /></label>
          <button type="button" className="text-button" disabled={readings.length === 3} onClick={() => {
            setReadings(previous => previous.filter(r => r.id !== p.id)); invalidate();
          }}>Remove HB reading {index+1}</button>
        </fieldset>)}
        <button type="button" className="secondary" disabled={readings.length === 1000} onClick={add}>Add HB reading</button>
        <div className="actions"><button className="primary" type="submit">Fit conventional HB</button></div>
      </fieldset></form>
      <div aria-busy={busy}><p role="status" className="status">{status}</p>{error && <p role="alert" className="error">{error}</p>}
        {result && <section aria-label="HB fit result"><h3>Bounded fit parameters · SI</h3>
          <p>τ₀: {display(result.parameters.yield_stress_pa.value)} Pa · K: {display(result.parameters.consistency_index_pa_s_n.value)} Pa·sⁿ · n: {display(result.parameters.flow_behavior_index.value)}</p>
          <table className="summary-table" aria-label="HB measured and predicted data"><caption>All entered observations; residual = predicted − measured</caption>
            <thead><tr>{['RPM', 'Dial', 'Shear rate (s⁻¹)', 'Measured stress (Pa)', 'Predicted stress (Pa)', 'Residual (Pa)'].map(label => <th scope="col" key={label}>{label}</th>)}</tr></thead>
            <tbody>{result.points.map(p => <tr key={p.rpm}>{[p.rpm, p.dial, p.shear_rate_s_inv, p.shear_stress_pa, p.predicted_stress_pa, p.residual_pa].map((v, i) => <td key={i}>{display(v)}</td>)}</tr>)}</tbody>
          </table>
          <h3>Residual diagnostics · {result.diagnostics.objective}</h3>
          <p>SSE: {display(result.diagnostics.sse_pa2)} Pa² · RMSE: {display(result.diagnostics.rmse_pa)} Pa · Maximum |residual|: {display(result.diagnostics.max_abs_residual_pa)} Pa</p>
          <p>Complete search: {result.diagnostics.evaluations} profiles; n ∈ [{result.diagnostics.n_min}, {result.diagnostics.n_max}], step {result.diagnostics.n_step}.
            {' '}Near-optimal n: {result.diagnostics.near_optimal_n_min}–{result.diagnostics.near_optimal_n_max} ({result.diagnostics.near_optimal_count} grid values; normalized mean squared error ≤ minimum + 10⁻⁶).
            {' '}Exponent at search bound: {result.diagnostics.at_n_bound ? 'yes' : 'no'}.</p>
          <p>{result.diagnostics.warning} Three readings provide no residual degrees of freedom. Small residuals do not validate a fluid model.</p>
          <div className="provenance"><strong>{result.model_id} v{result.model_version}</strong>
            <p>Input schema {result.input_schema_version} · Result schema {result.result_schema_version}</p>
            <p>{result.applicability.assumptions}</p><p>{result.applicability.limitations}</p></div>
        </section>}
        <p className="result-note">No extrapolated curve or uncertainty certification. Display rounding is not engineering accuracy. The supplied-parameter HB study remains separate.</p>
      </div>
    </div>
  </section>;
}
