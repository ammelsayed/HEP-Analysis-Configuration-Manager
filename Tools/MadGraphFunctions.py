import re
import numpy as np
import os
import glob

## logging method
tag = "[MadGraph_Functions]"
# out = logger.msg if logger is not None else print
out = print

def mg5_discover_event_files(main_dir, max_depth: int = 4):
    
    """
    Discover MadGraph5 sample folders and their files.

    A "sample folder" is a directory that contains (in the SAME folder):
      - at least one healthy *.root
      - parton_systematics.log
      - a banner file matching <folder_name>*banner.txt
      - (optional but reported) *.hepmc.gz and *.lhe.gz

    Input may point to:
      - a single sample folder (files directly inside)
      - a parent folder containing multiple sample folders (possibly nested)
      - a parent folder that contains an Events/ subfolder (MG5 default layout)

    The search strategy:
      - If input dir has an Events/ subdir, start from there (preferred).
      - Check the start directory itself: if it is a sample folder, return it only.
      - Otherwise, recursively search subfolders up to max_depth, collecting any sample folders found.

    Returns a list of dicts, one per discovered sample folder.
    """

    # Allow passing a list of directories directly.
    if isinstance(main_dir, list):
        all_results = []
        for d in main_dir:
            all_results.extend(mg5_discover_event_files(d, max_depth=max_depth))
        return all_results

    if not os.path.isdir(main_dir):
        out(f"{tag} Invalid directory: {main_dir}")
        return []

    # If MG5 default layout exists, search from Events/
    start_dir = os.path.join(main_dir, "Events")
    if not os.path.isdir(start_dir):
        start_dir = main_dir

    try:
        from Tools.DelphesFunctions import is_healty
    except Exception as e:
        out(f"{tag} Could not import is_healty for ROOT checks: {e}")
        is_healty = None

    def _pick_first(pattern):
        items = sorted(glob.glob(pattern))
        return items[0] if items else None

    def _find_healthy_root(dir_path):
        roots = sorted(glob.glob(os.path.join(dir_path, "*.root")))
        if not roots:
            return None, 0
        if is_healty is None:
            return roots[0], len(roots)
        for rf in roots:
            if is_healty(rf):
                return rf, len(roots)
        return None, len(roots)

    def _is_sample_dir(dir_path):
        folder_name = os.path.basename(os.path.normpath(dir_path))
        chosen_root, n_roots = _find_healthy_root(dir_path)
        if chosen_root is None:
            return None  # not a sample folder (or all roots unhealthy)

        parton = _pick_first(os.path.join(dir_path, "parton_systematics.log"))
        banner = _pick_first(os.path.join(dir_path, f"{folder_name}*banner.txt"))

        # Require these to be present in the same directory
        if parton is None or banner is None:
            return None

        hepmc = _pick_first(os.path.join(dir_path, "*.hepmc.gz"))
        lhe = _pick_first(os.path.join(dir_path, "*.lhe.gz"))

        return {
            "subfolder": folder_name,
            "subfolder_path": dir_path,
            "root_files": chosen_root,
            "hepmc_files": hepmc,
            "lhe_files": lhe,
            "parton_systematics_logs": parton,
            "banner_files": banner,
            "_n_root_candidates": n_roots,
        }

    # If the start_dir itself is already a sample folder, use it and stop.
    direct = _is_sample_dir(start_dir)
    if direct is not None:
        out(f"{tag} Sample files found directly in: {start_dir}")
        return [direct]

    # Otherwise search subfolders recursively.
    out(f"{tag} Searching for sample folders under: {start_dir}")

    results = []
    visited = set()

    # BFS by depth
    frontier = [(start_dir, 0)]
    while frontier:
        current, depth = frontier.pop(0)
        if current in visited:
            continue
        visited.add(current)

        if depth > max_depth:
            continue

        # list subdirs
        try:
            entries = sorted(os.listdir(current))
        except Exception:
            continue

        subdirs = [os.path.join(current, e) for e in entries if os.path.isdir(os.path.join(current, e))]
        if depth == 0:
            out(f"{tag} Found {len(subdirs)} subfolders in the Events folder, named : {[os.path.basename(s) for s in subdirs]}")

        for sd in subdirs:
            sample = _is_sample_dir(sd)
            name = os.path.basename(os.path.normpath(sd))

            if sample is not None:
                out(f"{tag} Scanning Events subfolder: {name}")
                out(f"{tag}  -> Using healthy ROOT file: {sample['root_files']}")
                out(f"{tag}  -> parton_systematics.log: {sample['parton_systematics_logs']}")
                out(f"{tag}  -> banner: {sample['banner_files']}")
                if sample["hepmc_files"] is None:
                    out(f"{tag}  -> HepMC not found in '{name}'.")
                else:
                    out(f"{tag}  -> HepMC: {sample['hepmc_files']}")
                if sample["lhe_files"] is None:
                    out(f"{tag}  -> LHE not found in '{name}'.")
                else:
                    out(f"{tag}  -> LHE: {sample['lhe_files']}")
                results.append(sample)
                # Do NOT descend into a directory that is already a valid sample folder
                continue

            # Not a sample folder; decide whether to descend
            # Only descend if it contains subdirectories (otherwise nothing to do)
            try:
                has_children = any(os.path.isdir(os.path.join(sd, x)) for x in os.listdir(sd))
            except Exception:
                has_children = False
            if has_children:
                frontier.append((sd, depth + 1))

    if len(results) == 0:
        out(f"{tag} No valid sample folders found under: {start_dir}")
    return results


def mg5_parton_systematics_txt_reader(filepath, use_fp = False):
    """
    This function reads the parton_sytematics.txt file generated by MadGraph5_aMC@NLO.
    It extracts the original cross-section, scale variation, central scheme variation, and PDF variation.
    Returns a dictionary with these values and the total uncertainty.

    To get this file while generating (LO) events, these setting has to be made in the run_card.dat file before generating the events:
    set use_syst True
	set systematics_program systematics
	set systematics_arguments ['--together=mur,muf,dyn', '--pdf=errorset']

    Args:
        filepath (str): Path to the 'parton_systematics.txt' file.
        use_fp (bool, optional): If True, convert cross-section from pb to fb
            (multiply by 1000). If False, keep in pb. Defaults to False.
    
    Returns:
        dict: Dictionary containing the following keys:
            - "Cross Section" (float): Cross-section value in pb (or fb if use_fp=True)
            - "Scale Variation" (list): [up, down] relative uncertainties from scale
              variations (as decimals, e.g., 0.05 for 5%)
            - "Central Scheme Variation" (list): [up, down] relative uncertainties
              from central scheme variations (as decimals)
            - "PDF Variation" (list): [up, down] relative uncertainties from PDF
              variations (as decimals)
            - "Total Uncertainty (relative)" (list): [up, down] combined relative
              uncertainties (quadrature sum of all variations)
            - "Total Uncertainty (absolute)" (list): [up, down] absolute uncertainties
              in the same units as "Cross Section"
            - "Upper/Lower Cross Sections" (list): [upper, lower] cross-section values
              including uncertainties (cross section ± total uncertainty)

    """
    pct_re = re.compile(r'([+-]?\s*\d+(?:\.\d+)?)\s*%')

    with open(filepath) as f:

        for line in f:
            
            if "original cross-section" in line:
                xsec_pb = float(line.split(":", 1)[1].strip())

            if "scale variation" in line:
                nums = pct_re.findall(line)
                if nums:
                    scale = [float(n.replace(" ", ""))/100.0 for n in nums]

            if "central scheme variation" in line:
                nums = pct_re.findall(line)
                if nums:
                    scheme = [float(n.replace(" ", ""))/100.0 for n in nums]

            if "PDF variation" in line:
                nums = pct_re.findall(line)
                if nums:
                    pdf = [float(n.replace(" ", ""))/100.0 for n in nums]

    # basic checks
    if xsec_pb is None:
        raise ValueError("original cross-section not found in file")

    # set default zero-uncertainties if any systematics block missing
    if scale is None:
        scale = [0.0, 0.0]
    if scheme is None:
        scheme = [0.0, 0.0]
    if pdf is None:
        pdf = [0.0, 0.0]
    
    # relative uncertainties calculations:
    up_rel = np.sqrt(scale[0]**2 + scheme[0]**2 + pdf[0]**2)
    down_rel = np.sqrt(scale[1]**2 + scheme[1]**2 + pdf[1]**2)

    # convert xsec to desried units
    if use_fp:
        xsec_converted = xsec_pb * 1000.0
    else:
        xsec_converted = xsec_pb * 1.0


    # upper and lower cross section values
    xsec_up = xsec_converted * (1.0 + up_rel)
    xsec_down = xsec_converted * (1.0 - down_rel)

    # absolute +delta and -delta values
    xsec_up_abs = xsec_converted * up_rel
    xsec_down_abs = xsec_converted * down_rel

    return {
        "Cross Section" : xsec_converted,
        "Scale Variation": scale,
        "Central Scheme Variation": scheme,
        "PDF Variation": pdf,
        "Total Uncertainty (relative)": [up_rel, down_rel],
        "Total Uncertainty (absolute)": [xsec_up_abs, xsec_down_abs],
        "Upper/Lower Cross Sections": [xsec_up, xsec_down]
    }


_PHASE_VAR_MAP = {
    "ptj":  "pt_jet",
    "ptb":  "pt_bjet",
    "ptl":  "pt_lepton",
    "pta":  "pt_photon",
    "ptt":  "pt_top",
    "ptt1": "pt_top1",
    "ptt2": "pt_top2",
    "etaj": "eta_jet",
    "etal": "eta_lepton",
    "etab": "eta_bjet",
    "mjj":  "m_jj",
    "mll":  "m_ll",
    "mll01": "m_ll01",
    "mll02": "m_ll02",
    "drjj": "dr_jj",
    "drll": "dr_ll",
    # extend as you meet more names in your banners
}
def mg5_parse_banner_phase_space_cuts(banner_file_path):
    """
    Parse a MadGraph5 banner.txt file and extract:
      - phase-space cuts (pt, eta, m, dR, etc.)
      - additional run information when easily available
    Returns a dictionary:
      {
        "phase_space_cuts": [
            {
              "variable": "<internal name>",
              "min": <float or -inf>,
              "max": <float or +inf>,
              "unit": "<string>",
              "raw_name": "<name in banner>",
              "raw_min": "<raw string>",
              "raw_max": "<raw string>",
            },
            ...
        ],
        "metadata": {
            ... other key/value pairs from banner (beam energy, pdf, etc.) when matched ...
        }
      }
    """
    phase_space_cuts = []
    metadata = {}
    if not os.path.isfile(banner_file_path):
        out(f"{tag} Banner file not found: {banner_file_path}")
        return {"phase_space_cuts": phase_space_cuts, "metadata": metadata}
    with open(banner_file_path, "r") as f:
        lines = f.readlines()
    # MG5 banners often have blocks like:
    #   #**********************************************************************
    #   #=========================== Run settings =============================
    #   ...
    # with lines such as:
    #   20.0 = ptj   # min pt for jets
    #   -1.0 = etaj  # min eta
    #   5.0  = etaj  # max eta
    #
    # We'll look for patterns "value = name" and try to interpret known cut variables.
    cut_pattern = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*=\s*([A-Za-z0-9_]+)")
    # Some cuts appear as "name = value"
    rev_cut_pattern = re.compile(r"^\s*([A-Za-z0-9_]+)\s*=\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)")
    # For each variable we might see two lines: one min and one max.
    # We'll collect all raw occurrences then post-process.
    raw_cuts = {}  # name -> list of (value, comment)
    for line in lines:
        # Strip comments but keep them separately for info
        parts = line.split("#", 1)
        core = parts[0].strip()
        comment = parts[1].strip() if len(parts) > 1 else ""
        if not core:
            continue
        m = cut_pattern.match(core)
        if m:
            value_str, name = m.groups()
            raw_cuts.setdefault(name, []).append((value_str, comment))
            continue
        m2 = rev_cut_pattern.match(core)
        if m2:
            name, value_str = m2.groups()
            raw_cuts.setdefault(name, []).append((value_str, comment))
            continue
    # Interpret raw_cuts as min/max where appropriate
    for name, entries in raw_cuts.items():
        internal_var = _PHASE_VAR_MAP.get(name, name)
        numeric_vals = []
        for value_str, comment in entries:
            try:
                numeric_vals.append((float(value_str), comment))
            except ValueError:
                continue
        if not numeric_vals:
            continue
        # Heuristics:
        # - If only one value -> treat as min with max = +inf (or the opposite depending on typical MG usage)
        # - If two values -> min = min(val), max = max(val)
        if len(numeric_vals) == 1:
            v, _ = numeric_vals[0]
            # For pt-like or m-like quantities: usually "min"
            if name.lower().startswith(("pt", "m", "ht")):
                vmin, vmax = v, float("inf")
            else:
                # For eta-like, MG often uses [-max, max]; but a single value is ambiguous.
                # Use [-inf, v] as a conservative default.
                vmin, vmax = float("-inf"), v
        else:
            vs = [v for v, _ in numeric_vals]
            vmin, vmax = min(vs), max(vs)
        unit = "GeV" if name.lower().startswith(("pt", "ht", "m")) else "dimensionless"
        phase_space_cuts.append({
            "variable": internal_var,
            "min": vmin,
            "max": vmax,
            "unit": unit,
            "raw_name": name,
            "raw_min": str(vmin),
            "raw_max": str(vmax),
        })
    # TODO (optional): parse more metadata (beam energy, PDF, scales, etc.) from other banner sections.
    # You can add more regexes here as needed.
    return {
        "phase_space_cuts": phase_space_cuts,
        "metadata": metadata,
    }
    
if __name__ == "__main__":

    test_directory = "/data/ammelsayed/Framework/Samples/sm_backgrounds/tt"

    files = discover_event_files(test_directory)

    for file in files:
        print(file["root_files"])
        print(file["parton_systematics_logs"])
        print(file["banner_files"])
        print("\n")