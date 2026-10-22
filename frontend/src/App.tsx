import { useEffect, useState } from 'react';
import { Results } from './Results';
import type { Inputs, Snapshot, SavedCase, Section } from './types';
import './styles.css';

const defaultSection: Section = { length_m: 100, pipe_id_m: 0.08, pipe_od_m: 0.1, hole_id_m: 0.2 };
const initial: Inputs = {
  sections: [{ ...defaultSection }], density_kg_m3: 1000, viscosity_pa_s: 0.1, flow_m3_s: 0.001,
};
const geometry = [
  ['length_m', 'Length (m)'], ['pipe_id_m', 'Pipe ID (m)'],
  ['pipe_od_m', 'Pipe OD (m)'], ['hole_id_m', 'Hole ID (m)'],
] as const;
const fluid = [
  ['density_kg_m3', 'Density (kg/m³)'], ['viscosity_pa_s', 'Viscosity (Pa·s)'], ['flow_m3_s', 'Flow (m³/s)'],
] as const;

async function request<T>(path: string, input?: Inputs): Promise<T> {
  const response = input ? await fetch(path, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
      input_schema_version: '1', input: { sections: input.sections.map(section => ({
        length_m: Number(section.length_m), pipe_id_m: Number(section.pipe_id_m),
        pipe_od_m: Number(section.pipe_od_m), hole_id_m: Number(section.hole_id_m),
      })),
      density_kg_m3: Number(input.density_kg_m3), viscosity_pa_s: Number(input.viscosity_pa_s), flow_m3_s: Number(input.flow_m3_s) },
    }),
  }) : await fetch(path);
  const body = await response.json().catch(() => {
    throw new Error(`Request failed (${response.status})`);
  });
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : `Request failed (${response.status})`);
  return body;
}

export default function App() {
  const [inputs, setInputs] = useState(initial);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [cases, setCases] = useState<SavedCase[]>([]);
  const [busy, setBusy] = useState('Loading cases');
  const [error, setError] = useState('');
  const [status, setStatus] = useState('Ready to calculate.');

  useEffect(() => {
    let active = true;
    request<SavedCase[]>('/api/v2/cases').then(records => { if (active) setCases(records); })
      .catch(reason => { if (active) setError(reason.message); })
      .finally(() => { if (active) setBusy(''); });
    return () => { active = false; };
  }, []);

  function edit(next: Inputs) {
    setInputs(next); setSnapshot(null); setError('');
    setStatus('Inputs changed. Calculate or save to produce new results.');
  }
  async function run(label: string, work: () => Promise<void>) {
    setBusy(label); setError('');
    try { await work(); }
    catch (reason) {
      setSnapshot(null);
      setStatus('Request failed. No new result is displayed.');
      setError(reason instanceof Error ? reason.message : 'Request failed');
    } finally { setBusy(''); }
  }
  function calculate(save: boolean) {
    void run(save ? 'Saving case' : 'Calculating', async () => {
      if (save) {
        const record = await request<SavedCase>('/api/v2/cases', inputs);
        setCases(previous => [...previous, record]);
        setSnapshot(record);
        setStatus(`Saved case ${record.id}. Results are a stored snapshot.`);
      } else {
        const calculated = await request<Snapshot>('/api/v2/calculate', inputs);
        setSnapshot(calculated); setStatus('Calculation complete. Not saved.');
      }
    });
  }

  return <>
    <a className="skip" href="#inputs">Skip to inputs</a>
    <header className="masthead">
      <div><p className="eyebrow">Independent engineering / Study series 01</p><h1>OpenOil<span>Drilling hydraulics</span></h1></div>
      <div className="stamp">HYD / 01<span>SI · VERTICAL · STEADY STATE</span><span>LOCAL ENGINEERING WORKBENCH</span></div>
    </header>
    <main>
      <aside className="scope" aria-label="Engineering scope warning">
        <strong>Study model / Explicit limits. No reference-solver parity claimed.</strong> Simplified Newtonian, incompressible, single-phase flow in a concentric vertical well. Not validated for field decisions or safety-critical pressure limits.
      </aside>
      <div className="workspace grid items-start gap-6">
        <section className="inputs panel" id="inputs" aria-labelledby="input-heading">
          <div className="section-heading"><p className="eyebrow">01 / Define the system</p><h2 id="input-heading">Geometry & circulation</h2></div>
          <form onSubmit={event => { event.preventDefault(); calculate(false); }}>
            <fieldset className="editor" disabled={!!busy}>
              <legend className="sr-only">Calculation inputs</legend>
              <p className="hint">Sections run from surface to bottom. Length = vertical depth increment; all dimensions are SI.</p>
              {inputs.sections.map((section, index) => <fieldset className="geometry" key={index}>
                <legend>Section {index + 1}</legend>
                <div className="field-grid">{geometry.map(([key, label]) => <label key={key}>{label}
                  <input type="number" step="any" required value={section[key]} onChange={event => edit({
                    ...inputs, sections: inputs.sections.map((old, i) => i === index ? { ...old, [key]: event.target.value } : old),
                  })} />
                </label>)}</div>
                <button className="text-button" type="button" disabled={inputs.sections.length === 1}
                  onClick={() => edit({ ...inputs, sections: inputs.sections.filter((_, i) => i !== index) })}>Remove section {index + 1}</button>
              </fieldset>)}
              <button className="secondary" type="button" onClick={() => edit({ ...inputs, sections: [...inputs.sections, { ...defaultSection }] })}>Add section</button>
              <p className="hint">Required: 0 &lt; pipe ID &lt; pipe OD &lt; hole ID; pipe OD / hole ID ≤ 0.8.</p>
              <h3>Fluid & flow</h3>
              <div className="fluid-grid">{fluid.map(([key, label]) => <label key={key}>{label}
                <input type="number" step="any" required value={inputs[key]} onChange={event => edit({ ...inputs, [key]: event.target.value })} />
              </label>)}</div>
              <p className="hint">Positive circulation only. Supported Re: &lt; 2,300 or 4,000–100,000 in both passages. Other regimes are rejected.</p>
              <div className="actions"><button className="primary" type="submit">Calculate</button>
                <button type="submit" formAction="" onClick={event => {
                  // Use native form validity for both submit actions.
                  if (event.currentTarget.form?.reportValidity()) { event.preventDefault(); calculate(true); }
                }}>Save case</button></div>
            </fieldset>
          </form>
          <p className="status" role="status">{busy ? `${busy}…` : status}</p>
          {error && <p role="alert" className="error">{error}</p>}
          <section className="case-library" aria-labelledby="cases-heading">
            <div className="library-heading"><h3 id="cases-heading">Case ledger</h3>
              <button type="button" disabled={!!busy} onClick={() => void run('Refreshing cases', async () => {
                setCases(await request<SavedCase[]>('/api/v2/cases')); setStatus('Case list refreshed.');
              })}>Refresh cases</button></div>
            {cases.length === 0 ? <p className="hint">No saved cases. Save a validated input to start the ledger.</p> :
              <ul>{cases.map(record => <li key={record.id}><button type="button" disabled={!!busy} onClick={() => void run(`Loading case ${record.id}`, async () => {
                const loaded = await request<SavedCase>(`/api/v2/cases/${record.id}`);
                setInputs(loaded.input); setSnapshot(loaded);
                setStatus(`Loaded case ${loaded.id}. Results are a stored snapshot.`);
              })}>Load case {record.id}<span>{record.input.sections.length} section(s) · {record.result.depth_m} m</span><span>{record.provenance ? `${record.provenance.model_id} · v${record.provenance.model_version}` : 'Unknown model · legacy snapshot'}</span></button></li>)}</ul>}
          </section>
        </section>
        <section className="results panel" aria-labelledby="results-heading" aria-busy={!!busy}>
          <div className="section-heading"><p className="eyebrow">02 / Inspect the response</p><h2 id="results-heading">Pressure & equivalent density</h2></div>
          {snapshot ? <Results snapshot={snapshot} /> :
            <div className="empty"><div className="well-icon" aria-hidden="true">↓</div><h3>Your pressure profile starts here.</h3><p>Define geometry, fluid and circulation. Calculate to inspect section friction, annular pressure and ECD.</p><span>NO RESULT / AWAITING CALCULATION</span></div>}
          <p className="result-note">Gauge pressure; zero surface annular pressure. Pipe friction is not standpipe pressure. No bit/nozzle or surface losses. Display rounding does not imply engineering accuracy.</p>
        </section>
      </div>
      <footer><strong>Know the boundary.</strong> No cuttings, bit optimization, swab/surge, real-time data or torque/drag. No eccentricity, roughness, inclination, non-Newtonian rheology or thermal effects. Independently validate before any engineering use.</footer>
    </main>
  </>;
}
