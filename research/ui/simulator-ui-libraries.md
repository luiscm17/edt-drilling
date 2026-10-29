# Simulator UI library research

This note records a shortlist for evolving OpenOil from calculator-style pages toward a simulator workspace with coordinated engineering plots and interactive well drawings. It is a research snapshot, not an implementation decision, performance benchmark, or claim of engineering correctness. The current frontend uses React 19, TypeScript 5.8, Vite 6, and Recharts 3 (`frontend/package.json`).

## Recommendation

Prototype a dockable workspace with **Dockview** and evaluate **Apache ECharts** for new scientific plots. Keep existing Recharts plots until migration demonstrates a concrete benefit. Start well schematics with SVG when practical; evaluate **Konva** if richer canvas interactions are required. Use **React Flow** only if the intended visual is genuinely a node-and-edge editor. Consider Plotly.js or uPlot only against a specific chart requirement and representative data.

Keep engineering calculations, units, and result identity in OpenOil's domain/API layer; treat these libraries as presentation and interaction tools. None establishes solver correctness or parity with WellPlan.

## Candidate comparison

| UI need | Candidate | Publicly documented strengths | Tradeoffs and fit |
|---|---|---|---|
| Dockable workspace | [Dockview](https://dockview.dev/docs/) | Docking layout manager with tabs, groups, split views, drag/drop, floating panels, popout windows, and React support. | Promising for configurable input, plot, and schematic panels. Verify layout persistence and accessibility in a prototype. The official site identifies MIT; npm metadata also reported MIT, while GitHub API metadata returned `NOASSERTION`; check the exact package license before adoption. |
| Scientific charts | [Apache ECharts](https://echarts.apache.org/en/feature.html) | Documents Canvas/SVG rendering, tooltip, zoom/pan, interactive components, and large-data/streaming capabilities. | Good candidate for depth, pressure, rheology, and sensitivity plots. Benchmark on OpenOil's realistic traces; documented scale claims are not a benchmark of our workload. Registry metadata reported Apache-2.0. |
| Broad chart coverage | [Plotly.js](https://plotly.com/javascript/) | Documents chart event hooks, zoom, selection, controls, and a wide range of chart types. | Consider if breadth or 3D plotting is a near-term need. Assess bundle weight and application integration before choosing it as the default chart renderer. Registry metadata reported MIT. |
| Dense time-series charts | [uPlot](https://github.com/leeoniya/uPlot) | Project README describes a small, fast time-series plotter and claims high rendering performance. | README explicitly says built-in drag-scrolling/panning is omitted due to interaction ambiguity and can be added externally. A focused option for dense time series, but more interaction behavior may need to be supplied. Treat performance figures as project claims until measured. Registry metadata reported MIT. |
| Interactive 2D drawings | [Konva](https://konvajs.org/docs/) / [react-konva](https://konvajs.org/docs/react/) | Konva documents a 2D canvas object model with shapes, events, animation, and drag/drop; it supports React integration. | Candidate for complex, frequently manipulated diagrams. Compare with SVG for accessibility, text selection, and simpler geometry. Registry metadata reported MIT. |
| Node/edge editor | [React Flow](https://reactflow.dev/learn) (`@xyflow/react`) | Documents customizable nodes and edges, drag/drop, selection, viewport controls, and editor-oriented interactions. | Good for flowcharts or graph-like configuration. A wellbore drawing may be geometric rather than graph-based, so use only if the domain interaction actually fits this model. Registry metadata reported MIT. |
| Optional 3D scene | [React Three Fiber](https://r3f.docs.pmnd.rs/getting-started/introduction) | React renderer for Three.js; its docs cover composing Three.js scenes from React components. | Defer unless a concrete 3D workflow requires it. Adds rendering and interaction complexity that a 2D schematic may not need. Registry metadata reported MIT. |

Versions observed in npm registry metadata during this research: Dockview 8.8.0, ECharts 6.1.0, Plotly.js 4.1.2, uPlot 1.6.32, `@xyflow/react` 12.12.0, `react-konva` 19.3.2, and `@react-three/fiber` 9.8.2. Registry versions and licenses are a point-in-time lookup, not an adoption or legal review. The official TanStack Table documentation URL checked during this pass returned 404; table-library selection is therefore left open rather than treated as verified.

## Reference interaction patterns from WellPlan Help

The locally installed WellPlan Help describes several patterns that may inform OpenOil's product design. These are **published-help descriptions**, not proof that the inspected WellPlan binary currently implements every behavior as described.

- **Workspace layout:** input tabs on the left, configuration tabs on the right, and plots/tables in a central output area (`c_nav_main_window.html`). Tabs and plots may be moved, floated, hidden, docked, and tiled into horizontal or vertical groups; layouts and plot order can be saved (`c_tabs.html`).
- **Coordinated plots:** the Data Reader shows the cursor's x/y position and may synchronize its movement across plots (`c_data_reader.html`). Plot zoom can be selected by dragging a region (`t_plot_manipulate.html`).
- **Connected workflow:** Help says some plot/table links activate the data-entry tab needed for that output (`c_visual_guides.html`).
- **Well schematic:** Help calls it an interactive view of the wellbore and downhole equipment; display options include hole section, string, both, and a to-scale or enlarged BHA view (`c_schematic_ov.html`, `t_schematic_change_display.html`). The T&D well schematic topic describes string-position output in the wellbore (`c_plot_td_well_schematic.html`).

Static inspection of WellPlan's managed executable and presentation assemblies found WPF/.NET Framework references, UI-related declared types, and installed `AvalonDock.dll` and `DynamicDataDisplay.dll`. These are **artifact observations only**; they do not establish which controls are active at runtime. WellPlan was not executed.

## Suggested evaluation before adoption

1. Build one representative workspace with a resizable plot, input panel, and schematic; test saving/restoring its layout.
2. Plot real OpenOil result shapes and units, then assess zoom, cursor readout, synchronized depth/cursor behavior, legends, resizing, and update frequency.
3. Test the schematic interaction separately: selection/hover, depth alignment, well geometry, keyboard access, and whether SVG or canvas is appropriate.
4. Measure bundle impact and responsiveness using representative datasets; do not rely on library marketing figures.
5. Check accessibility and licensing for the exact versions/packages selected. Keep plot and diagram interactions as views over domain/API results, not as sources of engineering calculations.

## Sources and scope

- Public documentation: the linked official project documentation and repositories in the comparison table; npm registry metadata was used for the point-in-time version/license observations.
- Local product reference: installed WellPlan Help topics named above, supplemented by static metadata from presentation assemblies. No target binaries were run or modified.
- No UI package was added and no performance, accessibility, or visual-parity test was performed in this research pass.
