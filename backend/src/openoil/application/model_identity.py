"""Independent OpenOil model identity, not a proprietary solver version."""

from datetime import UTC, datetime


def provenance():
    """Describe a newly computed snapshot; never apply to historical records."""
    return {
        "model_id": "openoil.hydraulics.newtonian-concentric-vertical",
        "model_version": "1.0.0",
        "units": "SI",
        "input_schema_version": "1",
        "result_schema_version": "1",
        "assumptions": [
            "Steady incompressible single-phase Newtonian flow; constant properties.",
            "Concentric vertical well; zero surface annular gauge pressure.",
            (
                "Laminar pipe 64/Re; exact concentric laminar annulus; smooth-wall Blasius "
                "with hydraulic diameter for turbulent annulus (approximation)."
            ),
            "Re < 2300 or 4000 <= Re <= 100000; pipe_OD/hole_ID <= 0.8.",
            (
                "No bit/nozzle, surface, roughness, eccentricity, inclination, rotation, "
                "cuttings, thermal, compressibility, transient or swab/surge effects."
            ),
            "Pipe friction is not standpipe pressure; not validated for field decisions.",
        ],
        "created_at": datetime.now(UTC).isoformat(),
    }
