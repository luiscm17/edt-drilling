import { useState } from 'react';

type Numeric = number | string;
type StudySection = { length_m: Numeric; pipe_od_m: Numeric; air_weight_n_m: Numeric };
type StudyInput = {
  sections: StudySection[]; inclination_deg: Numeric; density_kg_m3: Numeric;
  axial_friction_coefficient: Numeric; rotational_friction_coefficient: Numeric;
};
type Totals = { pickup_tension_n: number; slackoff_tension_n: number; rotating_torque_nm: number };
type Contribution = Totals & {
  submerged_weight_n_m: number; axial_gravity_n: number; normal_force_n: number;
  axial_friction_n: number; rotational_friction_n: number;
};
type StudyResult = Totals & { sections: Contribution[] };
const defaultSection: StudySection = { length_m: 100, pipe_od_m: 0.1, air_weight_n_m: 300 };
const geometry = [
  ['length_m', 'Study length (m)'], ['pipe_od_m', 'Study pipe OD (m)'], ['air_weight_n_m', 'Air weight (N/m)'],
] as const;
const conditions = [
  ['inclination_deg', 'Study inclination (° from vertical)'], ['density_kg_m3', 'Study density (kg/m³)'],
  ['axial_friction_coefficient', 'Axial friction coefficient (dimensionless)'],
  ['rotational_friction_coefficient', 'Rotational friction coefficient (dimensionless)'],
] as const;
const totals = [
  ['pickup_tension_n', 'Pickup surface tension', 'N'], ['slackoff_tension_n', 'Slackoff surface tension', 'N'],
  ['rotating_torque_nm', 'Rotating contact torque', 'N·m'],
] as const;
const columns = [
  ['submerged_weight_n_m', 'Submerged weight (N/m)'], ['axial_gravity_n', 'Axial gravity (N)'],
  ['normal_force_n', 'Normal force (N)'], ['axial_friction_n', 'Axial friction (N)'],
  ['rotational_friction_n', 'Rotational friction (N)'], ['pickup_tension_n', 'Pickup (N)'],
  ['slackoff_tension_n', 'Slackoff (N)'], ['rotating_torque_nm', 'Torque (N·m)'],
] as const;
const format = (value: number) => value.toLocaleString('en-US', { maximumFractionDigits: 2 });

export function TorqueDragStudy() {
  const [inputs, setInputs] = useState<StudyInput>({ sections: [{ ...defaultSection }], inclination_deg: 30,
    density_kg_m3: 1000, axial_friction_coefficient: 0.2, rotational_friction_coefficient: 0.3 });
  const [result, setResult] = useState<StudyResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('Calculate-only study. Not saved to the hydraulic ledger.');
  function edit(next: StudyInput) {
    setInputs(next); setResult(null); setError('');
    setStatus('Study inputs changed. Calculate again; no saved case is changed.');
  }
  async function calculate() {
    setBusy(true); setResult(null); setError(''); setStatus('Calculating study…');
    try {
      const response = await fetch('/api/torque-drag/calculate', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
          sections: inputs.sections.map(section => ({ length_m: Number(section.length_m),
            pipe_od_m: Number(section.pipe_od_m), air_weight_n_m: Number(section.air_weight_n_m) })),
          inclination_deg: Number(inputs.inclination_deg), density_kg_m3: Number(inputs.density_kg_m3),
          axial_friction_coefficient: Number(inputs.axial_friction_coefficient),
          rotational_friction_coefficient: Number(inputs.rotational_friction_coefficient),
        }),
      });
      const body = await response.json().catch(() => { throw new Error(`Request failed (${response.status})`); });
      if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : `Request failed (${response.status})`);
      setResult(body); setStatus('Study complete. Not saved; hydraulic ledger unchanged.');
    } catch (reason) {
      setResult(null); setError(reason instanceof Error ? reason.message : 'Request failed');
      setStatus('Study failed. No result is displayed; hydraulic ledger unchanged.');
    } finally { setBusy(false); }
  }
  return <section id="torque-drag" tabIndex={-1} className="torque-study panel" aria-labelledby="study-heading">
    <div className="section-heading study-heading"><div><p className="eyebrow">03 / Independent contact study</p>
      <h2 id="study-heading">Torque & drag study</h2></div><span className="study-badge">T&D / CALCULATE ONLY</span></div>
    <aside className="scope" aria-label="Torque and drag limitations">
      <strong>One straight, uniformly inclined well/string — no doglegs or buckling.</strong>
      Independent quasi-static weight/contact comparison; no field suitability or WellPlan parity claimed.
      Constant section weight/OD, fluid density and Coulomb friction; closed-pipe buoyancy envelope and freely suspended bottom.
      No bit load, internal fluid/open-end effects, tension-dependent normal force or axial/rotation coupling.
    </aside>
    <div className="study-layout">
      <form onSubmit={event => { event.preventDefault(); void calculate(); }}>
        <fieldset className="editor" disabled={busy}>
          <legend className="sr-only">Torque and drag study inputs</legend>
          <p className="hint">Independent inputs, not a saved hydraulic case. Sections are ordered surface to bottom; lengths are measured lengths, not vertical depths.</p>
          {inputs.sections.map((section, index) => <fieldset className="geometry" key={index}>
            <legend>Study section {index + 1}</legend>
            <div className="field-grid">{geometry.map(([key, label]) => <label key={key}>{label}
              <input type="number" step="any" min="0" required value={section[key]} onChange={event => edit({
                ...inputs, sections: inputs.sections.map((old, i) => i === index ? { ...old, [key]: event.target.value } : old),
              })} />
            </label>)}</div>
            <button className="text-button" type="button" disabled={inputs.sections.length === 1}
              onClick={() => edit({ ...inputs, sections: inputs.sections.filter((_, i) => i !== index) })}>Remove study section {index + 1}</button>
          </fieldset>)}
          <button type="button" onClick={() => edit({ ...inputs, sections: [...inputs.sections, { ...defaultSection }] })}>Add study section</button>
          <h3>Inclination, buoyancy & contact</h3>
          <div className="field-grid">{conditions.map(([key, label]) => <label key={key}>{label}
            <input type="number" step="any" min="0" required value={inputs[key]}
              onChange={event => edit({ ...inputs, [key]: event.target.value })} />
          </label>)}</div>
          <p className="hint">Positive section length, OD and air weight; 0 ≤ inclination &lt; 90°. Density and friction coefficients may be zero.
            The backend rejects nonpositive submerged weight or negative slackoff contributions.</p>
          <button className="primary" type="submit">Calculate study</button>
        </fieldset>
      </form>
      <div aria-busy={busy}>
        <h3>Surface loads / SI</h3>
        <p className="status" role="status">{status}</p>
        {error && <p className="error" role="alert">{error}</p>}
        {result ? <>
          <table className="summary-table" aria-label="Torque and drag SI summary">
            <thead><tr><th scope="col">Quantity</th><th scope="col">Value</th><th scope="col">Unit</th></tr></thead>
            <tbody>{totals.map(([key, label, unit]) => <tr key={key}><th scope="row">{label}</th><td>{format(result[key])}</td><td>{unit}</td></tr>)}</tbody>
          </table>
          <h3>Section audit / surface to bottom</h3>
          <p className="hint">Tensions and torque below are section contributions, not interface loads. Surface totals sum these contributions.</p>
          <div className="table-scroll" role="region" aria-label="Scrollable torque and drag contributions" tabIndex={0}>
            <table aria-label="Torque and drag section contributions">
              <thead><tr><th scope="col">Section</th>{columns.map(([key, label]) => <th scope="col" key={key}>{label}</th>)}</tr></thead>
              <tbody>{result.sections.map((section, index) => <tr key={index}><th scope="row">{index + 1}</th>
                {columns.map(([key]) => <td key={key}>{format(section[key])}</td>)}</tr>)}</tbody>
            </table>
          </div>
        </> : <p className="study-empty">NO STUDY RESULT / Awaiting a successful calculation</p>}
        <p className="result-note">Study results are temporary and never saved. Hydraulic cases retain their own inputs and snapshots.
          Values are rounded to at most two decimals in SI, not certified accuracy; small values can round to zero.
          Independent engineering validation is required before any engineering use.</p>
      </div>
    </div>
  </section>;
}
