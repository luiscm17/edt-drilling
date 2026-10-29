import { useState } from 'react';
import {
  CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer,
  Scatter, Tooltip, XAxis, YAxis,
} from 'recharts';

type Reading = { rpm: number; dial: number; shear_rate_s_inv: number; shear_stress_pa: number };
type CurvePoint = { rpm: number; shear_rate_s_inv: number; shear_stress_pa: number };
type Quantity = { quantity: string; value: number; unit: string };
type Result = {
  readings: Reading[]; model_curve: CurvePoint[];
  flow_behavior_index: Quantity; consistency_index: Quantity;
  model_id: string; model_version: string; input_schema_version: string; result_schema_version: string;
  applicability: { status: string; assumptions: string; limitations: string };
};
type Extra = { id: number; rpm: string; dial: string };

const number = (value: number, digits = 4) => value.toLocaleString('en-US', { maximumFractionDigits: digits });
function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}
function point(value: unknown): value is CurvePoint {
  return record(value) && typeof value.rpm === 'number' && Number.isFinite(value.rpm) && value.rpm > 0
    && typeof value.shear_rate_s_inv === 'number' && Number.isFinite(value.shear_rate_s_inv) && value.shear_rate_s_inv > 0
    && typeof value.shear_stress_pa === 'number' && Number.isFinite(value.shear_stress_pa) && value.shear_stress_pa > 0;
}
function reading(value: unknown): value is Reading {
  return record(value) && typeof value.rpm === 'number' && Number.isFinite(value.rpm) && value.rpm > 0
    && typeof value.shear_rate_s_inv === 'number' && Number.isFinite(value.shear_rate_s_inv) && value.shear_rate_s_inv > 0
    && typeof value.shear_stress_pa === 'number' && Number.isFinite(value.shear_stress_pa) && value.shear_stress_pa >= 0
    && typeof value.dial === 'number' && Number.isFinite(value.dial) && value.dial >= 0;
}
function quantity(value: unknown, name: string, unit: string): value is Quantity {
  return record(value) && value.quantity === name && value.unit === unit
    && typeof value.value === 'number' && Number.isFinite(value.value) && value.value > 0;
}
function validResult(value: unknown): value is Result {
  if (!record(value)) return false;
  const data = value as Partial<Result>;
  return Array.isArray(data.readings) && data.readings.length >= 2 && data.readings.every(reading)
    && Array.isArray(data.model_curve) && data.model_curve.length === data.readings.length
    && data.model_curve.every(point) && data.model_curve.every((model, index) =>
      model.rpm === data.readings?.[index].rpm && model.shear_rate_s_inv === data.readings[index].shear_rate_s_inv)
    && quantity(data.flow_behavior_index, 'flow_behavior_index', '1')
    && quantity(data.consistency_index, 'consistency_index', 'Pa·s^n')
    && data.model_id === 'openoil.rheology.fann-power-law' && data.model_version === '1.0.0'
    && data.input_schema_version === '1' && data.result_schema_version === '1'
    && record(data.applicability) && data.applicability.status === 'supported'
    && typeof data.applicability.assumptions === 'string' && data.applicability.assumptions.length > 0
    && typeof data.applicability.limitations === 'string' && data.applicability.limitations.length > 0;
}

export function PowerLawRheologyStudy() {
  const [dial300, setDial300] = useState('');
  const [dial600, setDial600] = useState('');
  const [extras, setExtras] = useState<Extra[]>([]);
  const [nextId, setNextId] = useState(1);
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('Enter positive 300 and 600 RPM readings. No hydraulic case is changed.');

  function invalidate() {
    setResult(null); setError(''); setStatus('Power Law inputs changed. Calculate again.');
  }
  function changeDial(rpm: 300 | 600, value: string) {
    if (rpm === 300) setDial300(value);
    else setDial600(value);
    invalidate();
  }
  function changeExtra(id: number, field: 'rpm' | 'dial', value: string) {
    setExtras(previous => previous.map(item => item.id === id ? { ...item, [field]: value } : item));
    invalidate();
  }
  function addExtra() {
    setExtras(previous => [...previous, { id: nextId, rpm: '', dial: '' }]);
    setNextId(previous => previous + 1); invalidate();
  }
  function removeExtra(id: number) {
    setExtras(previous => previous.filter(item => item.id !== id)); invalidate();
  }
  async function calculate() {
    setResult(null); setError('');
    const parsed: { rpm: number; dial: number }[] = [];
    for (const [rpm, raw] of [[300, dial300], [600, dial600]] as const) {
      const dial = Number(raw);
      if (raw.trim() === '' || !Number.isFinite(dial) || dial <= 0) {
        setError(`${rpm} rpm dial must be positive and finite`);
        setStatus('Invalid inputs. No result displayed.'); return;
      }
      parsed.push({ rpm, dial });
    }
    if (parsed[1].dial <= parsed[0].dial) {
      setError('600 rpm dial must exceed 300 rpm dial');
      setStatus('Invalid inputs. No result displayed.'); return;
    }
    for (const item of extras) {
      if (item.rpm.trim() === '' && item.dial.trim() === '') continue;
      const rpm = Number(item.rpm); const dial = Number(item.dial);
      if (item.rpm.trim() === '' || !Number.isFinite(rpm) || rpm <= 0 ||
          item.dial.trim() === '' || !Number.isFinite(dial) || dial < 0 ||
          parsed.some(other => other.rpm === rpm)) {
        setError('Optional readings need unique positive RPM and nonnegative finite dial values.');
        setStatus('Invalid inputs. No result displayed.'); return;
      }
      parsed.push({ rpm, dial });
    }
    setBusy(true); setStatus('Calculating Power Law rheology…');
    try {
      const response = await fetch('/api/v1/rheology/power-law/calculate', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ readings: parsed }),
      });
      const body: unknown = await response.json().catch(() => {
        throw new Error(`Request failed (${response.status})`);
      });
      if (!response.ok) {
        const detail = record(body) ? body.detail : undefined;
        throw new Error(typeof detail === 'string' ? detail : `Request failed (${response.status})`);
      }
      if (!validResult(body)) throw new Error('Invalid Power Law rheology response');
      setResult(body); setStatus('Calculation complete. Not saved; hydraulic cases unchanged.');
    } catch (reason) {
      setResult(null); setError(reason instanceof Error ? reason.message : 'Request failed');
      setStatus('Calculation failed. No result displayed; hydraulic cases unchanged.');
    } finally { setBusy(false); }
  }

  return <section id="power-law-rheology" tabIndex={-1} className="rheology-study panel" aria-labelledby="power-law-heading">
    <div className="section-heading study-heading">
      <div><p className="eyebrow">06 / Flow behavior · consistency · shear curve</p><h2 id="power-law-heading">Power Law rheology study</h2></div>
      <span className="study-badge">POWER LAW / CALCULATE ONLY</span>
    </div>
    <aside className="scope" aria-label="Power Law rheology study limitations">
      <strong>Two-point Power Law derivation; not a full rheology or hydraulics model.</strong>
      Positive 300/600 RPM readings define the curve. Other readings are observations, not fit parameters.
      No gels, downhole prediction, case persistence, hydraulic integration or field validation.
    </aside>
    <div className="study-layout">
      <form noValidate onSubmit={event => { event.preventDefault(); void calculate(); }}>
        <fieldset className="editor" disabled={busy}>
          <legend className="sr-only">Power Law rheology inputs</legend>
          <p className="hint" id="power-law-hint">Required dimensionless dials: 600 RPM must exceed 300 RPM; optional unique positive RPM readings may have zero dial.</p>
          <div className="rheology-required-grid">
            {([300, 600] as const).map(rpm => <label key={rpm}>{rpm} rpm dial reading
              <input type="number" step="any" min="0" required value={rpm === 300 ? dial300 : dial600}
                aria-describedby="power-law-hint" aria-invalid={error ? true : undefined}
                onChange={event => changeDial(rpm, event.target.value)} />
            </label>)}
          </div>
          <div className="rheology-extras">
            <h3>Additional observations / optional</h3>
            {extras.map((item, index) => <div className="rheology-extra-row" key={item.id}>
              <label>Optional reading {index + 1} RPM<input type="number" step="any" min="0" value={item.rpm}
                onChange={event => changeExtra(item.id, 'rpm', event.target.value)} /></label>
              <label>Optional reading {index + 1} dial reading<input type="number" step="any" min="0" value={item.dial}
                onChange={event => changeExtra(item.id, 'dial', event.target.value)} /></label>
              <button className="text-button" type="button" onClick={() => removeExtra(item.id)}>Remove optional reading {index + 1}</button>
            </div>)}
            <button className="secondary" type="button" onClick={addExtra}>Add optional reading</button>
          </div>
          <div className="actions"><button className="primary" type="submit">Calculate Power Law rheology</button></div>
        </fieldset>
      </form>
      <div aria-busy={busy}>
        <h3>Rheology results / SI</h3>
        <p className="status" role="status">{status}</p>
        {error && <p className="error" role="alert">{error}</p>}
        {result ? <>
          <div className="table-scroll"><table className="summary-table" aria-label="Power Law parameters">
            <thead><tr><th scope="col">Quantity</th><th scope="col">Value</th><th scope="col">Unit</th></tr></thead>
            <tbody>
              <tr><th scope="row">Flow behavior index (n)</th><td>{number(result.flow_behavior_index.value, 6)}</td><td>{result.flow_behavior_index.unit}</td></tr>
              <tr><th scope="row">Consistency index (K)</th><td>{number(result.consistency_index.value, 6)}</td><td>{result.consistency_index.unit}</td></tr>
            </tbody>
          </table></div>
          <figure><figcaption><h3>Shear stress vs shear rate</h3><p>Observed readings and derived 300/600 RPM Power Law relation; SI axes.</p></figcaption>
            <div className="chart" role="img" aria-label="Observed shear stress and derived Power Law model in SI units">
              <ResponsiveContainer width="100%" height={340} initialDimension={{ width: 640, height: 340 }}>
                <ComposedChart data={result.model_curve} margin={{ top: 24, right: 28, bottom: 24, left: 12 }}>
                  <CartesianGrid stroke="#d7d9d1" />
                  <XAxis type="number" dataKey="shear_rate_s_inv" domain={[0, 'dataMax']}
                    label={{ value: 'Shear rate (s⁻¹)', position: 'insideBottom', offset: -12 }} />
                  <YAxis type="number" label={{ value: 'Shear stress (Pa)', angle: -90, position: 'insideLeft' }} />
                  <Tooltip formatter={(value: number) => `${number(value)} Pa`}
                    labelFormatter={value => `Shear rate: ${number(Number(value), 3)} s⁻¹`} />
                  <Legend verticalAlign="top" />
                  <Line dataKey="shear_stress_pa" name="Derived Power Law model" stroke="#142b3b" strokeWidth={2}
                    dot={false} isAnimationActive={false} />
                  <Scatter data={result.readings} dataKey="shear_stress_pa" name="Observed readings" fill="#a64026" />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </figure>
          <div className="table-scroll"><table className="summary-table" aria-label="Power Law shear data">
            <thead><tr><th scope="col">RPM</th><th scope="col">Dial</th><th scope="col">Shear rate (s⁻¹)</th><th scope="col">Observed stress (Pa)</th><th scope="col">Model stress (Pa)</th></tr></thead>
            <tbody>{result.readings.map((item, index) => <tr key={item.rpm}>
              <td>{number(item.rpm, 2)}</td><td>{number(item.dial, 4)}</td>
              <td>{number(item.shear_rate_s_inv, 3)}</td><td>{number(item.shear_stress_pa, 4)}</td>
              <td>{number(result.model_curve[index].shear_stress_pa, 4)}</td>
            </tr>)}</tbody>
          </table></div>
          <div className="provenance"><strong>{result.model_id}</strong>
            <p>Model version {result.model_version} · Input schema {result.input_schema_version} · Result schema {result.result_schema_version}</p>
            <p>Applicability: {result.applicability.status}</p>
            <p>{result.applicability.assumptions}</p><p>{result.applicability.limitations}</p>
          </div>
        </> : <p className="study-empty">NO POWER LAW RESULT / Awaiting a successful calculation</p>}
        <div className="provenance rheology-formula"><strong>Documented transforms / independent SI calculation</strong>
          <p>γ (s⁻¹) = 1.70333 × RPM; τ (Pa) = 0.01065 × dial × 47.88025898033584.</p>
          <p>n = ln(θ₆₀₀/θ₃₀₀) / ln(2); K = τ₃₀₀ / γ₃₀₀ⁿ (Pa·s^n); τ = Kγⁿ. No reference-runtime parity claimed.</p>
        </div>
        <p className="result-note">Temporary result only; no saved case or hydraulic result changes. Display precision is not engineering accuracy.</p>
      </div>
    </div>
  </section>;
}
