import type { Inputs, Result } from './types';

const number = (value: number, digits = 0) => value.toLocaleString('en-US', { maximumFractionDigits: digits });

export function Results({ input, result }: { input: Inputs; result: Result }) {
  const maxLoss = Math.max(...result.sections.flatMap(section => [section.pipe.pressure_loss_pa, section.annulus.pressure_loss_pa]));
  let depth = 0;
  let friction = 0;
  const profile = [{ depth: 0, hydrostatic: 0, circulating: 0 }];
  result.sections.forEach((section, i) => {
    depth += Number(input.sections[i].length_m);
    friction += section.annulus.pressure_loss_pa;
    const hydrostatic = Number(input.density_kg_m3) * 9.80665 * depth;
    profile.push({ depth, hydrostatic, circulating: hydrostatic + friction });
  });
  const x = (pressure: number) => 65 + 420 * pressure / result.bottomhole_annular_pa;
  const y = (d: number) => 45 + 210 * d / result.depth_m;
  return <>
    <div className="table-scroll"><table aria-label="Pressure and density summary" className="summary-table">
      <thead><tr><th scope="col">Quantity</th><th scope="col">Value</th><th scope="col">Unit</th></tr></thead>
      <tbody>{([
        ['Vertical depth', result.depth_m, 'm'], ['Pipe friction total', result.pipe_friction_pa, 'Pa'],
        ['Annular friction total', result.annular_friction_pa, 'Pa'], ['Hydrostatic pressure', result.hydrostatic_pa, 'Pa'],
        ['Bottomhole annular pressure', result.bottomhole_annular_pa, 'Pa'], ['Equivalent circulating density (ECD)', result.ecd_kg_m3, 'kg/m³'],
      ] as const).map(([label, value, unit]) => <tr key={label}><th scope="row">{label}</th><td>{number(value, unit === 'kg/m³' ? 1 : 2)}</td><td>{unit}</td></tr>)}</tbody>
    </table></div>
    <figure>
      <figcaption><h3>Friction by section</h3><p>Separate pipe and annular loss magnitudes; same linear scale.</p></figcaption>
      <svg role="img" aria-label="Section friction losses in Pa, pipe and annulus" viewBox={`0 0 550 ${80 + result.sections.length * 58}`}>
        <title>Section friction losses</title><desc>Horizontal bars compare each section. Exact pressures and regimes are in the section table.</desc>
        <text x="110" y="18">0 Pa</text><text x="515" y="18" textAnchor="end">{number(maxLoss, 2)} Pa</text>
        {result.sections.map((section, index) => <g key={index}>
          <text x="12" y={51 + index * 58}>S{index + 1}</text>
          <rect className="pipe-fill" x="110" y={32 + index * 58} width={Math.max(0.5, section.pipe.pressure_loss_pa / maxLoss * 405)} height="14" />
          <rect className="annulus-fill" x="110" y={50 + index * 58} width={Math.max(0.5, section.annulus.pressure_loss_pa / maxLoss * 405)} height="14" />
        </g>)}
      </svg>
      <div className="legend"><span className="pipe-key">Pipe</span><span className="annulus-key">Annulus</span></div>
    </figure>
    <figure>
      <figcaption><h3>Annular pressure profile</h3><p>Section-boundary values; depth increases downwards.</p></figcaption>
      <svg role="img" aria-label="Annular pressure versus vertical depth, hydrostatic and circulating" viewBox="0 0 550 310">
        <title>Annular pressure versus vertical depth</title><desc>Dashed hydrostatic and solid circulating gauge pressure in Pa. Depth in metres. Curves may overlap when friction is small.</desc>
        {[0, 0.5, 1].map(fraction => <g key={fraction}>
          <line className="gridline" x1="65" x2="485" y1={y(result.depth_m * fraction)} y2={y(result.depth_m * fraction)} />
          <text x="55" y={y(result.depth_m * fraction) + 4} textAnchor="end">{number(result.depth_m * fraction, 1)}</text>
          <text x={65 + 420 * fraction} y="30" textAnchor="middle">{number(result.bottomhole_annular_pa * fraction)}</text>
        </g>)}
        <text x="275" y="13" textAnchor="middle">Gauge pressure (Pa)</text>
        <text x="18" y="155" transform="rotate(-90 18 155)" textAnchor="middle">Depth (m)</text>
        <polyline className="hydro-line" points={profile.map(p => `${x(p.hydrostatic)},${y(p.depth)}`).join(' ')} />
        <polyline className="pressure-line" points={profile.map(p => `${x(p.circulating)},${y(p.depth)}`).join(' ')} />
        {profile.map((p, index) => <circle className="annulus-fill" key={index} cx={x(p.circulating)} cy={y(p.depth)} r="3" />)}
      </svg>
      <div className="legend"><span className="hydro-key">Hydrostatic (dashed)</span><span className="annulus-key">Circulating</span></div>
      <p className="hint">Curves can overlap at low friction. See the table for exact differences.</p>
      <details><summary>Profile values (accessible data)</summary><div className="table-scroll"><table aria-label="Annular pressure profile values">
        <thead><tr><th scope="col">Depth (m)</th><th scope="col">Hydrostatic (Pa)</th><th scope="col">Circulating (Pa)</th></tr></thead>
        <tbody>{profile.map((p, i) => <tr key={i}><td>{number(p.depth, 2)}</td><td>{number(p.hydrostatic, 2)}</td><td>{number(p.circulating, 2)}</td></tr>)}</tbody>
      </table></div></details>
    </figure>
    <h3>Section audit</h3>
    <div className="table-scroll"><table aria-label="Section pressure losses">
      <thead><tr>{['Section', 'Passage', 'Loss (Pa)', 'Velocity (m/s)', 'Re', 'Darcy f', 'Regime'].map(label => <th scope="col" key={label}>{label}</th>)}</tr></thead>
      <tbody>{result.sections.flatMap((section, index) => (['pipe', 'annulus'] as const).map(passage => <tr key={`${index}-${passage}`}>
        <th scope="row">S{index + 1}</th><td>{passage}</td><td>{number(section[passage].pressure_loss_pa, 2)}</td>
        <td>{number(section[passage].velocity_m_s, 4)}</td><td>{number(section[passage].reynolds, 1)}</td>
        <td>{number(section[passage].darcy_factor, 5)}</td><td>{section[passage].regime}</td>
      </tr>))}</tbody>
    </table></div>
  </>;
}
