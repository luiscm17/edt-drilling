import { useState } from 'react';
import {
  CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer,
  Scatter, Tooltip, XAxis, YAxis,
} from 'recharts';

type Reading = { rpm: number; dial: number; shear_rate_s_inv: number; shear_stress_pa: number };
type Quantity = { quantity: string; value: number; unit: string };
type Applicability = { status: string; assumptions: string; limitations: string };
type Result = {
  readings: Reading[];
  plastic_viscosity: Quantity;
  yield_point: Quantity;
  model_id: string;
  model_version: string;
  input_schema_version: string;
  result_schema_version: string;
  applicability: Applicability;
};
type ExtraReading = { id: number; rpm: string; dial: string };

const number = (value: number, digits = 4) => value.toLocaleString('en-US', { maximumFractionDigits: digits });
const tick = (value: number) => value.toLocaleString('en-US', { notation: 'compact' });

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function validReading(value: unknown): value is Reading {
  if (!record(value)) return false;
  return typeof value.rpm === 'number' && Number.isFinite(value.rpm) && value.rpm > 0
    && typeof value.dial === 'number' && Number.isFinite(value.dial) && value.dial >= 0
    && typeof value.shear_rate_s_inv === 'number' && Number.isFinite(value.shear_rate_s_inv) && value.shear_rate_s_inv > 0
    && typeof value.shear_stress_pa === 'number' && Number.isFinite(value.shear_stress_pa) && value.shear_stress_pa >= 0;
}

function validQuantity(value: unknown, quantity: string, unit: string): value is Quantity {
  if (!record(value)) return false;
  return value.quantity === quantity && value.unit === unit
    && typeof value.value === 'number' && Number.isFinite(value.value) && value.value >= 0;
}

function validResult(body: unknown): body is Result {
  if (!record(body)) return false;
  const result = body as Partial<Result>;
  const applicability = result.applicability;
  return Array.isArray(result.readings) && result.readings.length >= 2
    && result.readings.every(validReading)
    && new Set(result.readings.map(reading => reading.rpm)).size === result.readings.length
    && result.readings.some(reading => reading.rpm === 300)
    && result.readings.some(reading => reading.rpm === 600)
    && validQuantity(result.plastic_viscosity, 'plastic_viscosity', 'Pa·s')
    && validQuantity(result.yield_point, 'yield_point', 'Pa')
    && result.model_id === 'openoil.rheology.fann-bingham'
    && result.model_version === '1.0.0'
    && result.input_schema_version === '1' && result.result_schema_version === '1'
    && record(applicability) && applicability.status === 'supported'
    && typeof applicability.assumptions === 'string' && applicability.assumptions.length > 0
    && typeof applicability.limitations === 'string' && applicability.limitations.length > 0;
}

export function BinghamRheologyStudy() {
  const [dial300, setDial300] = useState('');
  const [dial600, setDial600] = useState('');
  const [extras, setExtras] = useState<ExtraReading[]>([]);
  const [nextExtraId, setNextExtraId] = useState(1);
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('Enter the 300 and 600 RPM dial readings. Calculate-only; no hydraulic case is changed.');

  function invalidate(message: string) {
    setResult(null);
    setError('');
    setStatus(message);
  }

  function editDial(which: '300' | '600', value: string) {
    if (which === '300') setDial300(value);
    else setDial600(value);
    invalidate('Bingham inputs changed. Calculate again; no hydraulic case is changed.');
  }

  function editExtra(id: number, field: 'rpm' | 'dial', value: string) {
    setExtras(previous => previous.map(reading => reading.id === id ? { ...reading, [field]: value } : reading));
    invalidate('Bingham inputs changed. Calculate again; no hydraulic case is changed.');
  }

  function addExtra() {
    setExtras(previous => [...previous, { id: nextExtraId, rpm: '', dial: '' }]);
    setNextExtraId(previous => previous + 1);
    invalidate('Optional reading added. Enter its RPM and dial value.');
  }

  function removeExtra(id: number) {
    setExtras(previous => previous.filter(reading => reading.id !== id));
    invalidate('Optional reading removed. Calculate again to refresh the graph.');
  }

  async function calculate() {
    setResult(null);
    setError('');
    const entries: { rpm: number; dial: number }[] = [];
    for (const [rpm, dial] of [[300, dial300], [600, dial600]] as const) {
      if (dial.trim() === '') {
        setError(`Enter a nonnegative finite dial reading for ${rpm} RPM.`);
        setStatus('Invalid inputs. No result is displayed.');
        return;
      }
      const value = Number(dial);
      if (!Number.isFinite(value) || value < 0) {
        setError(`Enter a nonnegative finite dial reading for ${rpm} RPM.`);
        setStatus('Invalid inputs. No result is displayed.');
        return;
      }
      entries.push({ rpm, dial: value });
    }
    for (const reading of extras) {
      if (reading.rpm.trim() === '' && reading.dial.trim() === '') continue;
      if (reading.rpm.trim() === '' || reading.dial.trim() === '') {
        setError('Complete each optional reading or remove it.');
        setStatus('Invalid inputs. No result is displayed.');
        return;
      }
      const rpm = Number(reading.rpm);
      const dial = Number(reading.dial);
      if (!Number.isFinite(rpm) || rpm <= 0) {
        setError('RPM readings must be unique positive finite numbers.');
        setStatus('Invalid inputs. No result is displayed.');
        return;
      }
      if (!Number.isFinite(dial) || dial < 0) {
        setError('Dial readings must be nonnegative finite numbers.');
        setStatus('Invalid inputs. No result is displayed.');
        return;
      }
      entries.push({ rpm, dial });
    }
    if (new Set(entries.map(reading => reading.rpm)).size !== entries.length) {
      setError('RPM readings must be unique positive finite numbers.');
      setStatus('Invalid inputs. No result is displayed.');
      return;
    }

    setBusy(true);
    setStatus('Calculating Bingham rheology…');
    try {
      const response = await fetch('/api/v1/rheology/bingham/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ readings: entries }),
      });
      const body: unknown = await response.json().catch(() => {
        throw new Error(`Request failed (${response.status})`);
      });
      if (!response.ok) {
        const detail = record(body) ? body.detail : undefined;
        throw new Error(typeof detail === 'string' ? detail : `Request failed (${response.status})`);
      }
      if (!validResult(body)) throw new Error('Invalid Bingham rheology response');
      setResult(body);
      setStatus('Calculation complete. Not saved; hydraulic cases unchanged.');
    } catch (reason) {
      setResult(null);
      setError(reason instanceof Error ? reason.message : 'Request failed');
      setStatus('Calculation failed. No result is displayed; hydraulic cases unchanged.');
    } finally {
      setBusy(false);
    }
  }

  const maximumRate = result ? Math.max(...result.readings.map(reading => reading.shear_rate_s_inv)) : 0;
  const modelLine = result ? [
    { shear_rate_s_inv: 0, shear_stress_pa: result.yield_point.value },
    {
      shear_rate_s_inv: maximumRate,
      shear_stress_pa: result.yield_point.value + result.plastic_viscosity.value * maximumRate,
    },
  ] : [];

  return <section id="bingham-rheology" tabIndex={-1} className="rheology-study panel" aria-labelledby="bingham-rheology-heading">
    <div className="section-heading study-heading">
      <div><p className="eyebrow">05 / Viscosity · yield · shear curve</p><h2 id="bingham-rheology-heading">Bingham rheology study</h2></div>
      <span className="study-badge">BINGHAM / CALCULATE ONLY</span>
    </div>
    <aside className="scope" aria-label="Bingham rheology study limitations">
      <strong>Two-point Bingham derivation; not a full rheology or hydraulics model.</strong>
      Plastic viscosity and yield point come only from 300/600 RPM readings. Additional readings are plotted as observations, not fit parameters.
      No gel strengths, other rheology models, hydraulic integration, case persistence or field validation.
    </aside>
    <div className="study-layout">
      <form noValidate onSubmit={event => { event.preventDefault(); void calculate(); }}>
        <fieldset className="editor" disabled={busy}>
          <legend className="sr-only">Bingham rheology inputs</legend>
          <p className="hint" id="bingham-input-hint">Dial readings are nonnegative and dimensionless. The 300 and 600 RPM values are required; extra RPM values are optional.</p>
          <div className="rheology-required-grid">
            <label>300 rpm dial reading
              <input type="number" step="any" min="0" required value={dial300} aria-describedby="bingham-input-hint"
                aria-invalid={error ? true : undefined} onChange={event => editDial('300', event.target.value)} />
            </label>
            <label>600 rpm dial reading
              <input type="number" step="any" min="0" required value={dial600} aria-describedby="bingham-input-hint"
                aria-invalid={error ? true : undefined} onChange={event => editDial('600', event.target.value)} />
            </label>
          </div>
          <div className="rheology-extras">
            <h3>Additional observations / optional</h3>
            {extras.map((reading, index) => <div className="rheology-extra-row" key={reading.id}>
              <label>Optional reading {index + 1} RPM
                <input type="number" step="any" min="0" value={reading.rpm} aria-describedby="bingham-input-hint"
                  aria-invalid={error ? true : undefined} onChange={event => editExtra(reading.id, 'rpm', event.target.value)} />
              </label>
              <label>Optional reading {index + 1} dial reading
                <input type="number" step="any" min="0" value={reading.dial} aria-describedby="bingham-input-hint"
                  aria-invalid={error ? true : undefined} onChange={event => editExtra(reading.id, 'dial', event.target.value)} />
              </label>
              <button className="text-button" type="button" onClick={() => removeExtra(reading.id)}>Remove optional reading {index + 1}</button>
            </div>)}
            <button className="secondary" type="button" onClick={addExtra}>Add optional reading</button>
          </div>
          <div className="actions"><button className="primary" type="submit">Calculate Bingham rheology</button></div>
        </fieldset>
      </form>
      <div aria-busy={busy}>
        <h3>Rheology results / SI</h3>
        <p className="status" role="status">{status}</p>
        {error && <p className="error" role="alert">{error}</p>}
        {result ? <>
          <div className="table-scroll">
            <table className="summary-table" aria-label="Bingham rheology parameters">
              <thead><tr><th scope="col">Quantity</th><th scope="col">Value</th><th scope="col">Unit</th></tr></thead>
              <tbody>
                <tr><th scope="row">Plastic viscosity</th><td>{number(result.plastic_viscosity.value, 6)}</td><td>{result.plastic_viscosity.unit}</td></tr>
                <tr><th scope="row">Yield point</th><td>{number(result.yield_point.value, 4)}</td><td>{result.yield_point.unit}</td></tr>
              </tbody>
            </table>
          </div>
          <figure>
            <figcaption><p className="eyebrow">01 / Measured points and derived model</p><h3>Shear stress vs shear rate</h3>
              <p>Observed readings and the 300/600 RPM Bingham relation. Axes use SI units.</p></figcaption>
            <div className="chart" role="img" aria-label="Observed shear stress and derived Bingham model in SI units">
              <ResponsiveContainer width="100%" height={340} initialDimension={{ width: 640, height: 340 }}>
                <ComposedChart data={modelLine} margin={{ top: 24, right: 28, bottom: 24, left: 12 }}>
                  <CartesianGrid stroke="#d7d9d1" />
                  <XAxis type="number" dataKey="shear_rate_s_inv" domain={[0, 'dataMax']} tickFormatter={tick}
                    label={{ value: 'Shear rate (s⁻¹)', position: 'insideBottom', offset: -12 }} />
                  <YAxis type="number" tickFormatter={tick} label={{ value: 'Shear stress (Pa)', angle: -90, position: 'insideLeft' }} />
                  <Tooltip formatter={(value: number) => `${number(value, 4)} Pa`}
                    labelFormatter={value => `Shear rate: ${number(Number(value), 3)} s⁻¹`} />
                  <Legend verticalAlign="top" />
                  <Line dataKey="shear_stress_pa" name="Derived Bingham model" stroke="#142b3b" strokeWidth={2}
                    dot={false} isAnimationActive={false} />
                  <Scatter data={result.readings} dataKey="shear_stress_pa" name="Observed readings" fill="#a64026" />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </figure>
          <div className="table-scroll">
            <table className="summary-table" aria-label="Rheology shear data">
              <thead><tr><th scope="col">RPM</th><th scope="col">Dial</th><th scope="col">Shear rate (s⁻¹)</th><th scope="col">Observed stress (Pa)</th><th scope="col">Model stress (Pa)</th></tr></thead>
              <tbody>{result.readings.map(reading => <tr key={reading.rpm}>
                <td>{number(reading.rpm, 2)}</td><td>{number(reading.dial, 4)}</td>
                <td>{number(reading.shear_rate_s_inv, 3)}</td><td>{number(reading.shear_stress_pa, 4)}</td>
                <td>{number(result.yield_point.value + result.plastic_viscosity.value * reading.shear_rate_s_inv, 4)}</td>
              </tr>)}</tbody>
            </table>
          </div>
          <div className="provenance">
            <strong>{result.model_id}</strong>
            <p>Model version {result.model_version} · Input schema {result.input_schema_version} · Result schema {result.result_schema_version}</p>
            <p>Applicability: {result.applicability.status}</p>
            <p>{result.applicability.assumptions}</p><p>{result.applicability.limitations}</p>
          </div>
        </> : <p className="study-empty">NO BINGHAM RESULT / Awaiting a successful calculation</p>}
        <div className="provenance rheology-formula">
          <strong>Documented transforms / independent SI calculation</strong>
          <p>γ (s⁻¹) = 1.70333 × RPM; τ (Pa) = 0.01065 × dial × 47.88025898033584.</p>
          <p>PV = (τ₆₀₀ − τ₃₀₀) / (γ₆₀₀ − γ₃₀₀); YP = τ₃₀₀ − PV × γ₃₀₀. Additional readings are observations only. No reference-runtime parity is claimed.</p>
        </div>
        <p className="result-note">Temporary result only; no saved case, hydraulic result or ledger entry changes. Display precision is not engineering accuracy. Independently validate before engineering use.</p>
      </div>
    </div>
  </section>;
}
