import { useState } from 'react';

type Component = { length_m: number; inner_diameter_m: number; pressure_pa: number };
type Quantity = { quantity: string; value: number; unit: string };
type Result = {
  gel_stress: Quantity; pressure: Quantity; components: Component[];
  source: { rpm: number; dial: number; stress_lb_ft2_per_dial: number; lb_ft2_to_pa: number };
  scope: string; model_id: string; model_version: string;
  input_schema_version: string; result_schema_version: string;
  applicability: { status: string; assumptions: string; limitations: string };
};
type Draft = { id: number; length: string; diameter: string };
const display = (value: number) => value.toLocaleString('en-US', { maximumFractionDigits: 4 });
const record = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null;
const positive = (value: unknown) => typeof value === 'number' && Number.isFinite(value) && value > 0;
const nonnegative = (value: unknown) => typeof value === 'number' && Number.isFinite(value) && value >= 0;

function validResult(value: unknown, count: number): value is Result {
  if (!record(value) || !record(value.source) || !record(value.gel_stress)
    || !record(value.pressure) || !record(value.applicability)) return false;
  return value.model_id === 'openoil.rheology.fann-zero-second-gel-break-pressure'
    && value.scope === 'string interior only' && value.model_version === '1.0.0'
    && value.input_schema_version === '1' && value.result_schema_version === '1'
    && value.source.rpm === 3 && nonnegative(value.source.dial)
    && value.source.stress_lb_ft2_per_dial === 0.01065
    && value.source.lb_ft2_to_pa === 47.88025898033584
    && value.gel_stress.quantity === 'zero_second_gel_stress' && value.gel_stress.unit === 'Pa'
    && nonnegative(value.gel_stress.value)
    && value.pressure.quantity === 'interior_break_gel_pressure' && value.pressure.unit === 'Pa'
    && nonnegative(value.pressure.value)
    && Array.isArray(value.components) && value.components.length === count
    && value.components.every((part: unknown) => record(part) && positive(part.length_m)
      && positive(part.inner_diameter_m) && nonnegative(part.pressure_pa))
    && value.applicability.status === 'supported'
    && typeof value.applicability.assumptions === 'string'
    && typeof value.applicability.limitations === 'string';
}

export function GelBreakPressureStudy() {
  const [dial, setDial] = useState('');
  const [components, setComponents] = useState<Draft[]>([{ id: 1, length: '', diameter: '' }]);
  const [nextId, setNextId] = useState(2);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState('Enter a 3 rpm dial reading and string-interior component geometry.');
  function invalidate() {
    setResult(null); setError(''); setStatus('Inputs changed. Calculate again; no case was saved.');
  }
  function edit(id: number, field: 'length' | 'diameter', value: string) {
    setComponents(previous => previous.map(part => part.id === id ? { ...part, [field]: value } : part));
    invalidate();
  }
  function add() {
    setComponents(previous => [...previous, { id: nextId, length: '', diameter: '' }]);
    setNextId(id => id + 1); invalidate();
  }
  function remove(id: number) {
    setComponents(previous => previous.filter(part => part.id !== id)); invalidate();
  }
  async function calculate() {
    setResult(null); setError('');
    if (dial.trim() === '' || !nonnegative(Number(dial))) {
      setError('Enter a nonnegative finite 3 rpm dial reading.'); return;
    }
    const parts = components.map(part => ({ length_m: Number(part.length), inner_diameter_m: Number(part.diameter) }));
    if (components.some(part => part.length.trim() === '' || part.diameter.trim() === '')
      || parts.some(part => !positive(part.length_m) || !positive(part.inner_diameter_m))) {
      setError('Enter positive finite length and inner diameter for each component.'); return;
    }
    setBusy(true); setStatus('Calculating string-interior break-gel pressure…');
    try {
      const response = await fetch('/api/v1/rheology/gel-break-pressure/calculate', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dial_3_rpm: Number(dial), components: parts }),
      });
      const body: unknown = await response.json();
      if (!response.ok) {
        const detail = record(body) ? body.detail : undefined;
        throw new Error(typeof detail === 'string' ? detail : `Request failed (${response.status})`);
      }
      if (!validResult(body, parts.length)) throw new Error('Invalid gel-break response');
      setResult(body); setStatus('Calculation complete. Not saved; hydraulic cases unchanged.');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Request failed');
      setStatus('Calculation failed. No result is displayed.');
    } finally { setBusy(false); }
  }
  return <section id="gel-break-pressure" tabIndex={-1} className="rheology-study panel" aria-labelledby="gel-heading">
    <div className="section-heading study-heading"><div><p className="eyebrow">09 / Gel · string interior</p>
      <h2 id="gel-heading">Gel and break pressure study</h2></div>
      <span className="study-badge">ZERO-SECOND / CALCULATE ONLY</span></div>
    <aside className="scope" aria-label="Gel and break pressure limitations">
      <strong>String interior only; not a complete WellPlan pressure analysis.</strong>
      Zero-second gel derives from the 3 rpm Fann dial. Excludes timed gels, annulus, tool joints, hydraulic coupling and field validation.
    </aside>
    <div className="study-layout">
      <form noValidate onSubmit={event => { event.preventDefault(); void calculate(); }}>
        <fieldset className="editor" disabled={busy}>
          <legend>Fann reading and drillstring components</legend>
          <label>3 rpm dial reading<input type="number" min="0" step="any" value={dial}
            onChange={event => { setDial(event.target.value); invalidate(); }} /></label>
          <p className="hint">Dial is dimensionless. Each component has positive length and inner diameter in metres.</p>
          {components.map((part, index) => <fieldset className="geometry" key={part.id}>
            <legend>Component {index + 1}</legend>
            <label>Component {index + 1} length (m)<input type="number" step="any" min="0" value={part.length}
              onChange={event => edit(part.id, 'length', event.target.value)} /></label>
            <label>Component {index + 1} inner diameter (m)<input type="number" step="any" min="0" value={part.diameter}
              onChange={event => edit(part.id, 'diameter', event.target.value)} /></label>
            <button type="button" className="text-button" disabled={components.length === 1}
              onClick={() => remove(part.id)}>Remove component {index + 1}</button>
          </fieldset>)}
          <button className="secondary" type="button" onClick={add}>Add component</button>
          <div className="actions"><button className="primary" type="submit">Calculate interior break-gel pressure</button></div>
        </fieldset>
      </form>
      <div aria-busy={busy}>
        <p role="status" className="status">{status}</p>
        {error && <p role="alert" className="error">{error}</p>}
        {result && <section aria-label="Gel and interior pressure result">
          <h3>String interior only</h3>
          <p>Zero-second gel stress: {display(result.gel_stress.value)} Pa (3 rpm dial {display(result.source.dial)})</p>
          <p>Interior break-gel pressure: {display(result.pressure.value)} Pa</p>
          <table aria-label="Interior break-gel component pressures"><caption>Component breakdown · string interior only</caption>
            <thead><tr><th scope="col">Component</th><th scope="col">Length (m)</th>
              <th scope="col">Inner diameter (m)</th><th scope="col">Pressure (Pa)</th></tr></thead>
            <tbody>{result.components.map((part, index) => <tr key={index}><th scope="row">{index + 1}</th>
              <td>{display(part.length_m)}</td><td>{display(part.inner_diameter_m)}</td>
              <td>{display(part.pressure_pa)}</td></tr>)}</tbody></table>
          <p className="result-note">Model {result.model_id} v{result.model_version}. {result.applicability.limitations}</p>
        </section>}
      </div>
    </div>
  </section>;
}
