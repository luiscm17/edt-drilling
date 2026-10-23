import { useState } from 'react';

const fields = [
  ['density_kg_m3', 'Bit/nozzle density (kg/m³)'],
  ['flow_m3_s', 'Bit/nozzle flow (m³/s)'],
  ['total_nozzle_area_m2', 'Bit/nozzle total flow area (m²)'],
] as const;

type Result = {
  pressure_loss: { quantity: string; value: number; unit: string };
  model_id: string; model_version: string; input_schema_version: string; result_schema_version: string;
  coefficient: { symbol: string; value: number; unit: string; selection: string };
  applicability: { status: string; assumptions: string; limitations: string };
};

function validResult(body: unknown): body is Result {
  if (!body || typeof body !== 'object') return false;
  const result = body as Partial<Result>;
  return result.pressure_loss?.quantity === 'bit_nozzle_pressure_loss'
    && result.pressure_loss.unit === 'Pa'
    && typeof result.pressure_loss.value === 'number'
    && Number.isFinite(result.pressure_loss.value) && result.pressure_loss.value > 0
    && result.model_id === 'openoil.hydraulics.documented-bit-nozzle-pressure-loss'
    && result.model_version === '1.0.0'
    && result.input_schema_version === '1' && result.result_schema_version === '1'
    && result.coefficient?.symbol === 'Cd' && result.coefficient.value === 0.95
    && result.coefficient.unit === '1' && result.coefficient.selection === 'fixed documented coefficient'
    && result.applicability?.status === 'supported'
    && typeof result.applicability.assumptions === 'string' && result.applicability.assumptions.length > 0
    && typeof result.applicability.limitations === 'string' && result.applicability.limitations.length > 0;
}

export function BitNozzlePressureLossStudy() {
  const [inputs, setInputs] = useState({ density_kg_m3: '', flow_m3_s: '', total_nozzle_area_m2: '' });
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('Enter density, flow and total area. Calculate-only; no saved case is changed.');
  function edit(key: keyof typeof inputs, value: string) {
    setInputs(previous => ({ ...previous, [key]: value }));
    setResult(null); setError('');
    setStatus('Bit/nozzle inputs changed. Calculate again; hydraulic ledger unchanged.');
  }
  async function calculate() {
    setResult(null); setError('');
    const data = { density_kg_m3: Number(inputs.density_kg_m3), flow_m3_s: Number(inputs.flow_m3_s),
      total_nozzle_area_m2: Number(inputs.total_nozzle_area_m2) };
    if (Object.values(data).some(value => !Number.isFinite(value) || value <= 0)) {
      setError('Enter positive finite density, flow and total nozzle area in SI units.');
      setStatus('Invalid inputs. No result is displayed.'); return;
    }
    setBusy(true); setStatus('Calculating bit/nozzle pressure loss…');
    try {
      const response = await fetch('/api/v1/bit-nozzle-pressure-loss/calculate', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
      });
      const body: unknown = await response.json().catch(() => { throw new Error(`Request failed (${response.status})`); });
      if (!response.ok) {
        const detail = body && typeof body === 'object' && 'detail' in body ? body.detail : undefined;
        throw new Error(typeof detail === 'string' ? detail : `Request failed (${response.status})`);
      }
      if (!validResult(body)) throw new Error('Invalid bit/nozzle pressure-loss response');
      setResult(body); setStatus('Calculation complete. Not saved; hydraulic ledger unchanged.');
    } catch (reason) {
      setResult(null); setError(reason instanceof Error ? reason.message : 'Request failed');
      setStatus('Calculation failed. No result is displayed; hydraulic ledger unchanged.');
    } finally { setBusy(false); }
  }
  return <section id="bit-nozzle-pressure-loss" tabIndex={-1} className="nozzle-study panel" aria-labelledby="bit-loss-heading">
    <div className="section-heading study-heading"><div><p className="eyebrow">04 / Documented pressure contribution</p>
      <h2 id="bit-loss-heading">Bit/nozzle pressure-loss study</h2></div><span className="study-badge">BIT LOSS / CALCULATE ONLY</span></div>
    <aside className="scope" aria-label="Bit/nozzle pressure-loss limitations">
      <strong>One bit/nozzle contribution — not standpipe pressure or an operating limit.</strong>
      Steady incompressible single-phase flow, constant density and effective nozzle area. No system optimization,
      parasitic/tool-joint or surface losses, erosion, non-Newtonian, compressible, transient or multiphase effects.
      Independent implementation of documented equations; not validated for field decisions.
    </aside>
    <div className="study-layout">
      <form noValidate onSubmit={event => { event.preventDefault(); void calculate(); }}>
        <fieldset className="editor" disabled={busy}>
          <legend className="sr-only">Bit/nozzle pressure-loss inputs</legend>
          <p className="hint" id="bit-loss-hint">Positive finite SI inputs. Total effective flow area is the sum of all nozzle areas, not a diameter or one nozzle's area. Only use within the stated single-phase incompressible assumptions.</p>
          <div className="fluid-grid">{fields.map(([key, label]) => <label key={key}>{label}
            <input type="number" step="any" min="0" required value={inputs[key]} aria-describedby="bit-loss-hint"
              aria-invalid={error && !busy ? true : undefined} onChange={event => edit(key, event.target.value)} />
          </label>)}</div>
          <div className="actions"><button className="primary" type="submit">Calculate bit/nozzle pressure loss</button></div>
        </fieldset>
      </form>
      <div aria-busy={busy}>
        <h3>Bit/nozzle pressure-loss contribution / SI</h3>
        <p className="status" role="status">{status}</p>
        {error && <p className="error" role="alert">{error}</p>}
        {result ? <>
          <table className="summary-table" aria-label="Bit/nozzle pressure-loss SI result">
            <thead><tr><th scope="col">Quantity</th><th scope="col">Value</th><th scope="col">Unit</th></tr></thead>
            <tbody><tr><th scope="row">Bit/nozzle pressure loss</th><td>{result.pressure_loss.value.toLocaleString('en-US', { maximumFractionDigits: 4 })}</td><td>{result.pressure_loss.unit}</td></tr></tbody>
          </table>
          <div className="provenance">
            <strong>{result.model_id}</strong>
            <p>Model version {result.model_version} · Input schema {result.input_schema_version} · Result schema {result.result_schema_version}</p>
            <p>{result.coefficient.symbol} = {result.coefficient.value} (dimensionless) · {result.coefficient.selection}</p>
            <p>Applicability: {result.applicability.status}</p>
            <p>{result.applicability.assumptions}</p><p>{result.applicability.limitations}</p>
          </div>
        </> : <p className="study-empty">NO BIT/NOZZLE RESULT / Awaiting a successful calculation</p>}
        <div className="provenance nozzle-formula">
          <strong>Documented equations / fixed Cd = 0.95</strong>
          <p>v (ft/s) = Cd × Q (US gpm) / (2.96 × A (in²)); convert velocity to m/s, then ΔP (Pa) = ρ (kg/m³) × v² / (2 × Cd²).</p>
          <p>The literal 2.96 is retained from installed help, not replaced by coherent-SI Q/A. Documentation and independent unit conversion are the model basis, not a vendor-runtime parity claim.</p>
        </div>
        <p className="result-note">Temporary result only; no save action, aggregate, base hydraulic result or case snapshot changes.
          Display rounds to at most four decimals; small values may round to zero. Digits are not accuracy. Independently validate before engineering use.</p>
      </div>
    </div>
  </section>;
}
