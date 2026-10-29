import { useState } from 'react';
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';

type Parameter = { value: number; unit: string };
type Point = { shear_rate_s_inv: number; shear_stress_pa: number };
type Result = {
  parameters: Record<string, Parameter>;
  curve: Point[];
  model_id: string; model_version: string; input_schema_version: string; result_schema_version: string;
  applicability: { status: string; assumptions: string; limitations: string };
};
const fields = [
  ['reference_stress_pa', 'Reference stress (Pa)', 'Pa', true],
  ['zero_shear_stress_pa', 'Zero-shear stress (Pa)', 'Pa', false],
  ['high_shear_viscosity_pa_s', 'High-shear viscosity (Pa·s)', 'Pa·s', false],
  ['stress_exponent', 'Stress exponent (m)', '1', true],
  ['rate_exponent', 'Rate exponent (n)', '1', true],
] as const;
type Field = typeof fields[number][0];
const empty: Record<Field, string> = {
  reference_stress_pa: '', zero_shear_stress_pa: '', high_shear_viscosity_pa_s: '',
  stress_exponent: '', rate_exponent: '',
};
const number = (value: number, digits = 4) => value.toLocaleString('en-US', { maximumFractionDigits: digits });
function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}
function validResult(value: unknown): value is Result {
  if (!record(value) || !record(value.parameters) || !Array.isArray(value.curve) || !value.curve.length) return false;
  const parameters = value.parameters;
  if (!value.curve.every((point: unknown) => record(point)
    && typeof point.shear_rate_s_inv === 'number' && Number.isFinite(point.shear_rate_s_inv) && point.shear_rate_s_inv >= 0
    && typeof point.shear_stress_pa === 'number' && Number.isFinite(point.shear_stress_pa) && point.shear_stress_pa >= 0)) return false;
  if (!fields.every(([key, , unit, positive]) => {
    const parameter = parameters[key];
    return record(parameter) && parameter.unit === unit && typeof parameter.value === 'number'
      && Number.isFinite(parameter.value) && (positive ? parameter.value > 0 : parameter.value >= 0);
  })) return false;
  return value.model_id === 'openoil.rheology.generalized-herschel-bulkley-parametric'
    && value.model_version === '1.0.0' && value.input_schema_version === '1'
    && value.result_schema_version === '1' && record(value.applicability)
    && value.applicability.status === 'supported'
    && typeof value.applicability.assumptions === 'string' && value.applicability.assumptions.length > 0
    && typeof value.applicability.limitations === 'string' && value.applicability.limitations.length > 0;
}

export function GeneralizedHBRheologyStudy() {
  const [values, setValues] = useState<Record<Field, string>>(empty);
  const [rateText, setRateText] = useState('');
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('Supply SI parameters and explicit shear rates. No case is changed.');
  function invalidate() {
    setResult(null); setError(''); setStatus('Parameters changed. Evaluate again.');
  }
  function change(key: Field, value: string) {
    setValues(previous => ({ ...previous, [key]: value })); invalidate();
  }
  async function evaluate() {
    setResult(null); setError('');
    const parameters: Record<Field, number> = {} as Record<Field, number>;
    for (const [key, label, , positive] of fields) {
      const raw = values[key]; const value = Number(raw);
      if (raw.trim() === '' || !Number.isFinite(value) || (positive ? value <= 0 : value < 0)) {
        setError(`${label} must be ${positive ? 'positive' : 'nonnegative'} and finite.`);
        setStatus('Invalid parameters. No result displayed.'); return;
      }
      parameters[key] = value;
    }
    const parts = rateText.split(',').map(part => part.trim());
    const rates = parts.map(Number);
    if (parts.some(part => part === '') || rates.some(rate => !Number.isFinite(rate) || rate < 0)
        || new Set(rates).size !== rates.length) {
      setError('Shear rates must be unique nonnegative finite numbers.');
      setStatus('Invalid shear rates. No result displayed.'); return;
    }
    setBusy(true); setStatus('Evaluating generalized rheology…');
    try {
      const response = await fetch('/api/v1/rheology/generalized-hb/calculate', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...parameters, shear_rates_s_inv: rates }),
      });
      const body: unknown = await response.json().catch(() => {
        throw new Error(`Request failed (${response.status})`);
      });
      if (!response.ok) {
        const detail = record(body) ? body.detail : undefined;
        throw new Error(typeof detail === 'string' ? detail : `Request failed (${response.status})`);
      }
      if (!validResult(body)) throw new Error('Invalid generalized rheology response');
      setResult(body); setStatus('Evaluation complete. No case saved.');
    } catch (reason) {
      setResult(null); setError(reason instanceof Error ? reason.message : 'Request failed');
      setStatus('Evaluation failed. No result displayed.');
    } finally { setBusy(false); }
  }
  return <section id="generalized-hb-rheology" tabIndex={-1} className="rheology-study panel" aria-labelledby="ghb-heading">
    <div className="section-heading study-heading"><div>
      <p className="eyebrow">07 / Generalized parametric curve</p>
      <h2 id="ghb-heading">Generalized Herschel–Bulkley study</h2></div>
      <span className="study-badge">PARAMETRIC / CALCULATE ONLY</span>
    </div>
    <aside className="scope" aria-label="Generalized rheology study limitations">
      <strong>Evaluate supplied parameters only.</strong> No Fann fit, foam pressure model, hydraulic coupling, saved case or field validation. The curve contains no measured points.
    </aside>
    <div className="study-layout">
      <form noValidate onSubmit={event => { event.preventDefault(); void evaluate(); }}>
        <fieldset className="editor" disabled={busy}>
          <legend className="sr-only">Generalized rheology SI parameters</legend>
          <p className="hint">Enter all parameters in SI; no defaults are inferred. m and n are dimensionless.</p>
          <div className="rheology-required-grid">{fields.map(([key, label, , positive]) => <label key={key}>{label}
            <input type="number" step="any" min="0" required={positive} value={values[key]}
              aria-invalid={error ? true : undefined} onChange={event => change(key, event.target.value)} />
          </label>)}</div>
          <label>Shear rates (s⁻¹), comma-separated
            <input type="text" required value={rateText} placeholder="0, 40, 100"
              aria-invalid={error ? true : undefined} onChange={event => { setRateText(event.target.value); invalidate(); }} />
          </label>
          <div className="actions"><button className="primary" type="submit">Evaluate generalized rheology</button></div>
        </fieldset>
      </form>
      <div aria-busy={busy}>
        <h3>Modeled response / SI</h3><p className="status" role="status">{status}</p>
        {error && <p className="error" role="alert">{error}</p>}
        {result ? <>
          <div className="table-scroll"><table className="summary-table" aria-label="Generalized rheology parameters">
            <thead><tr><th scope="col">Parameter</th><th scope="col">Value</th><th scope="col">Unit</th></tr></thead>
            <tbody>{fields.map(([key, label]) => <tr key={key}><th scope="row">{label}</th>
              <td>{number(result.parameters[key].value, 6)}</td><td>{result.parameters[key].unit}</td></tr>)}</tbody>
          </table></div>
          <figure><figcaption><h3>Modeled shear stress vs shear rate</h3>
            <p>Curve from supplied parameters only; no observed Fann readings or pressure prediction.</p></figcaption>
            <div className="chart" role="img" aria-label="Generalized rheology model curve in SI units">
              <ResponsiveContainer width="100%" height={340} initialDimension={{ width: 640, height: 340 }}>
                <LineChart data={result.curve} margin={{ top: 24, right: 28, bottom: 24, left: 12 }}>
                  <CartesianGrid stroke="#d7d9d1" />
                  <XAxis type="number" dataKey="shear_rate_s_inv" label={{ value: 'Shear rate (s⁻¹)', position: 'insideBottom', offset: -12 }} />
                  <YAxis type="number" label={{ value: 'Shear stress (Pa)', angle: -90, position: 'insideLeft' }} />
                  <Tooltip formatter={(value: number) => `${number(value)} Pa`}
                    labelFormatter={value => `Shear rate: ${number(Number(value))} s⁻¹`} />
                  <Line dataKey="shear_stress_pa" name="Modeled stress (Pa)" stroke="#142b3b" strokeWidth={2}
                    isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </figure>
          <div className="table-scroll"><table className="summary-table" aria-label="Generalized rheology curve data">
            <thead><tr><th scope="col">Shear rate (s⁻¹)</th><th scope="col">Modeled stress (Pa)</th></tr></thead>
            <tbody>{result.curve.map(point => <tr key={point.shear_rate_s_inv}>
              <td>{number(point.shear_rate_s_inv, 3)}</td><td>{number(point.shear_stress_pa, 4)}</td>
            </tr>)}</tbody>
          </table></div>
          <div className="provenance"><strong>{result.model_id}</strong>
            <p>Model version {result.model_version} · Input schema {result.input_schema_version} · Result schema {result.result_schema_version}</p>
            <p>Applicability: {result.applicability.status}</p>
            <p>{result.applicability.assumptions}</p><p>{result.applicability.limitations}</p>
          </div>
        </> : <p className="study-empty">NO GENERALIZED RHEOLOGY RESULT / Awaiting evaluation</p>}
        <div className="provenance rheology-formula"><strong>Documented dimensionless relation</strong>
          <p>(τ/τ_ref)^m = (τ_z/τ_ref)^m + (μ_h γ/τ_ref)^n. No reference-runtime parity claimed.</p>
        </div>
        <p className="result-note">Temporary modeled curve only. Display precision is not engineering accuracy.</p>
      </div>
    </div>
  </section>;
}
