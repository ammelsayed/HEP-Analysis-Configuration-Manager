

## -------------------------------------------------------------------------- ##
##    Author:    A.M.M Elsayed                                                ##
##    Email:     ahmedphysica@outlook.com                                     ##
##    Institute: University of Science and Technology of China                ##
## -------------------------------------------------------------------------- ##                        



import json
import os
from Tools.DelphesFunctions import get_root_files_from_directory
from Tools.DelphesFunctions import root_events_number_reader
from Tools.DelphesFunctions import is_healty
from Tools.MadGraphFunctions import mg5_parton_systematics_txt_reader
from Tools.MadGraphFunctions import mg5_discover_event_files
from Tools.MadGraphFunctions import mg5_parse_banner_phase_space_cuts

## logging method
tag = "[Configurator]"
out = print

class Configurator:

    """
    Configuration manager for Monte Carlo analysis.
    """
    
    def __init__(self, config_file=None):

        if config_file and os.path.exists(config_file):
            self.data = self.load_config(config_file)

        else:
            self.data = {
                "version": "2.0.0",
                "analysis_description": None,
                "integrated_luminosity/pb": 400.0 * 1e3,  # pb^-1
                "processes": []
            }
        
        # List of unsupported Monte Carlo generators (not handled by this configurator)
        self.unsupported_generators = [
            "Sherpa", "Herwig", "Whizard","PythiaStandalone", 
            "CompHEP","CalcHEP","MC@NLO","POWHEG-BOX", 
            "Powheg"
        ]
    
    def set_analysis_description(self, description):
        """
        Set a description for the analysis
        
        Args:
            description (str): A brief description of the analysis setup and goals
        """
        self.data["analysis_description"] = description

    def set_luminosity(self, luminosity):
        """
        Set the integrated luminosity for the analysis
        
        Args:
            luminosity (float): Integrated luminosity in pb^-1
        """
        self.data["integrated_luminosity/pb"] = luminosity
    
    def add_process(self, process_info):
        """
        Add a process to the configuration
        
        Args:
            process_info (dict): Process information with the following structure:
                {
                    "category": "Background",  # or "Signal"
                    "name": "tt",
                    "sub_category": "Multitop",
                    "nlo_systematics_file": "/path/to/nlo_systematics.txt",  # Optional for NLO corrections


                    # For the events, you can add the directories and the systematic files, phase space cuts, lables by yourself, or 
                    # just give the directory to the configuration manager and it will figure out all these by itself, according to the generator
                    # you used,
                    "events": [  # List of phase space slices
                        {   
                            "generator" : "MadGraph5",
                            "qcd_order" : "LO", or "NLO" for example
                            "directories": "path/to/files",  # Will create a list of root files directoties found in this directory like: ["/path/to/file1.root", "/path/to/file2.root" ... ].
                            "phase_space_cuts": [  # Cuts specific to this slice
                                {
                                    "variable": "pt_top",
                                    "min": 200,
                                    "max": 400,
                                    "unit": "GeV"
                                }
                            ],
                            "systematics_file": "/path/to/parton_systematics.txt",  # Systematics for this slice
                            "cross_section": 920.0,  # Optional for K-factor of this slice
                            "slice_weight": 1.0,  # Optional manual weight for this slice
                            "slice_label": "low_pt"  # Label for this slice
                        },
                        {
                            "directories": ["/path/to/high_pt_file.root"],
                            "phase_space_cuts": [
                                {
                                    "variable": "pt_top",
                                    "min": 400,
                                    "max": float('inf'),
                                    "unit": "GeV"
                                }
                            ],
                            "systematics_file": "/path/to/high_pt_systematics.txt",
                            "cross_section": 980.0,  # Different NLO XS for this slice
                            "slice_label": "high_pt"
                        }
                    ],
                    "visualization": {
                        "color": 632,
                        "style": "stack"
                    },
                    "legend": "t#bar{t}",
                    "description": "Top pair production with phase space slicing"
                }
        """
        # ---- Basic validation for category and name ----
        category_raw = process_info.get("category")
        name = process_info.get("name")
        valid_categories = {"background", "signal", "data"}
        if not category_raw:
            out(f"{tag} The category of this process must be clarified.")
            return
        category = str(category_raw).strip().lower()
        if category not in valid_categories:
            out(f"{tag} Invalid category '{category_raw}'. Allowed: {sorted(valid_categories)}.")
            return
        if not name or not str(name).strip():
            out(f"{tag} A unique name for this process must be added.")
            return
        name = str(name).strip()
        # ---- Uniqueness check for process name ----
        existing_names = {p.get("name") for p in self.data.get("processes", [])}
        if name in existing_names:
            out(f"{tag} Process name '{name}' already exists. Please choose a unique name.")
            return
        # If we reach here, category & name are valid and unique
        process_info["category"] = category.capitalize()
        process_info["name"] = name
        out(f"{tag} Adding the {category} process: {name}")

        # --------------------------------------------------------------------
        # (A) Get inclusive cross section for the process if provided
        # --------------------------------------------------------------------
        # The NLO or higher corrections are usually calculated for the inclusive phase space and provided here. 
        if "nlo_systematics_file" in process_info and process_info["nlo_systematics_file"]:
            nlo_syst_data = mg5_parton_systematics_txt_reader(process_info["nlo_systematics_file"])
            nlo_cross_section =  nlo_syst_data["Cross Section"]
            process_info["nlo_cross_section"] = nlo_cross_section
            process_info["nlo_xsec_systematics"] = {
                "qcd_scale_variation" : nlo_syst_data["Scale Variation"],
                "central scheme_variation" : nlo_syst_data["Central Scheme Variation"],
                "pdf_variation" : nlo_syst_data["PDF Variation"]
            }
        else:
            out(f"{tag} No 'nlo_systematics_file' provided. It is strongly recommended to supply one in order to compute k-factors for each sample. Without it, k-factors and associated systematic uncertainties cannot be automatically calculated. Please consider providing a valid file path for 'nlo_systematics_file'.")

        # --------------------------------------------------------------------
        # (B) Figure out the MC generator used to automatically get all the data:
        # --------------------------------------------------------------------
        # The NLO or higher corrections are usually calculated for the inclusive phase space and provided here. 
        if "data" in process_info and process_info["data"]:
            data = process_info["data"]
            if "generator" in data and data["generator"]:
                mc_generator = data["generator"]
                # MadGraph5 Case
                if mc_generator.lower() in ["madgraph", "madgraph5", "madgraph5_amc@NLO"]:
                    out(f"{tag} Using existing tools for reading files generated by 'MadGraph5_aMC@NLO':")

                    directory = data["directory"]
                    # Accept either a single directory or a list of directories.
                    directories = directory if isinstance(directory, list) else [directory]

                    process_info["samples"] = []
                    samples = process_info["samples"]

                    for d in directories:
                        if not os.path.isdir(d):
                            out(f"{tag} Invalid directory : {d}")
                            continue

                        files = mg5_discover_event_files(d)
                        for f in files:
                            samples.append({
                                "lhe_file_path":        f["lhe_files"],
                                "hepmc_file_path":      f["hepmc_files"],
                                "root_file_path":       f["root_files"],
                                "xsec_systematics_file_path": f["parton_systematics_logs"],
                                "banner_file_path":     f["banner_files"],
                                "label":                "",
                                "description":          "",
                            })

                    if len(samples) == 0:
                        out(f"{tag} No usable samples found in provided directory/directories: {directories}")
                        return
    
                # Other generators functions can be added here         
                elif mc_generator.lower() in self.unsupported_generators:
                    out(f"{tag} Sorry, no support for the generator '{mc_generator}' now. Please contact the author to provide you this feature if needed.")
                    return
                else:
                    out(f"{tag} Unrecognized generator : {mc_generator}")
                    out(f"{tag} Please load each root file with its corresponding process number of events and cross section manually.\n")
                    return
        
        # Prepare events data
        for slice_info in process_info["samples"]:
        
            # --------------------------------------------------------------------
            # (1) Find all the root files given in the directory, check their health status, 
            # and create a list of directories of the root files.
            # --------------------------------------------------------------------
            # root_entry = slice_info["directories"]
            # # Case 1: user provided a directory path
            # if os.path.isdir(root_entry):
            #     try:
            #         root_files = get_root_files_from_directory(root_entry)
            #         slice_info["directories"] = root_files
            #         out(f"{tag} Found {len(root_files)} ROOT files in directory: {root_entry}")
            #     except Exception as e:
            #         out(f"{tag} Error accessing directory: {root_entry}. Exception: {e}")
            #         continue
            # # Case 2: user provided a list (should be list of ROOT files)
            # elif isinstance(root_entry, list):
            #     invalid = [
            #         f for f in root_entry
            #         if (not isinstance(f, str)) or (not f.endswith(".root"))
            #     ]
            #     if invalid:
            #         out(f"{tag} Invalid 'directories' list in slice: {slice_info.get('slice_label', '')}. ")
            #         out(f"{tag} Please include a list of ROOT file paths only. Invalid entries: {invalid}")
            #         continue
            #     # Optional: health check on each ROOT file
            #     healthy_files = []
            #     for f in root_entry:
            #         if not is_healty(f):
            #             out(f"{tag} Skipping unhealthy ROOT file: {f}")
            #         else:
            #             healthy_files.append(f)
            #     if not healthy_files:
            #         out(f"{tag} No healthy ROOT files found in 'directories' list for slice: ")
            #         out(f"{tag} {slice_info.get('slice_label', '')}.")
            #         continue
            #     slice_info["directories"] = healthy_files
            # # Case 3: user provided a single ROOT file path as string
            # elif isinstance(root_entry, str):
            #     if not root_entry.endswith(".root"):
            #         out(f"{tag} Invalid 'directories' value in slice: {slice_info.get('slice_label', '')}. ")
            #         out(f"{tag} Expected a ROOT file path ending with '.root', got: {root_entry}")
            #         continue
            #     if not is_healty(root_entry):
            #         out(f"{tag} Unhealthy ROOT file given in 'directories': {root_entry}")
            #         continue
            #     # keep as single string, or wrap in list depending on your convention
            #     # slice_info["directories"] = [root_entry]
            #     slice_info["directories"] = root_entry
            # # Case 4: anything else is invalid
            # else:
            #     out(f"{tag} Invalid type for 'directories' in slice: {slice_info.get('slice_label', '')}.")
            #     out(f"{tag} Expected directory path (str), ROOT file path (str), or list of ROOT paths, got {type(root_entry)}.")

            # --------------------------------------------------------------------
            # (2) Calculate the total number of events
            # --------------------------------------------------------------------
            n_events = root_events_number_reader(slice_info["root_file_path"])
            slice_info["number_events"] = n_events
            
            # --------------------------------------------------------------------
            # (3) Read systematics for this slice if provided
            # --------------------------------------------------------------------
            if "xsec_systematics_file_path" in slice_info and slice_info["xsec_systematics_file_path"]:
                # Cross section and its systematics
                # out(f"{tag} Using MadGraph5 tools to read cross seciton and its systematics.")
                syst_data = mg5_parton_systematics_txt_reader(slice_info["xsec_systematics_file_path"])
                cross_section = syst_data["Cross Section"]
                slice_info["cross_section"] = cross_section
                slice_info["xsec_systematics"] = {
                    "qcd_scale_variation" : syst_data["Scale Variation"],
                    "central scheme_variation" : syst_data["Central Scheme Variation"],
                    "pdf_variation" : syst_data["PDF Variation"]
                }
                # Calculate weight and k-factor for this slice
                if n_events and n_events > 0:
                    lum = self.data["integrated_luminosity/pb"]
                    weight = (cross_section * lum) / n_events
                    slice_info["weight"] = weight
                    # Calculate K-factor for this slice if NLO cross-section is provided
                    if "nlo_cross_section" in process_info and process_info["nlo_cross_section"]:
                        k_factor = process_info["nlo_cross_section"] / cross_section
                        slice_info["k_factor"] = k_factor
                    else:
                        slice_info["k_factor"] = 1.0
            
            # --------------------------------------------------------------------
            # (4) Read #banner.txt file to understand what this sample means
            # --------------------------------------------------------------------
            # **** Needs a fix *****
            if "banner_file_path" in slice_info and slice_info["banner_file_path"]:
                slice_info["phase_space_cuts"] = None
                slice_info["banner_metadata"] = None

                # banner_path = slice_info["banner_file_path"]
                # banner_info = mg5_parse_banner_phase_space_cuts(banner_path)
                # # Attach phase-space cuts in your internal format
                # if banner_info["phase_space_cuts"]:
                #     slice_info["phase_space_cuts"] = banner_info["phase_space_cuts"]
                # # Optionally attach metadata as well
                # if banner_info["metadata"]:
                #     slice_info["banner_metadata"] = banner_info["metadata"]
            else:
                out(f"{tag} Banner file not provided.")

        # --------------------------------------------------------------------
        # (4) Confirm the standarization of the json file 
        # --------------------------------------------------------------------
        # Each process should have a full visulation and legends items.
        if "visualization" in process_info and process_info["visualization"]:
            defaults = {
                "LineColor": None,
                "LineWidth": None,
                "LineStyle": None,
                "FillColor": None,
                "FillStyle": None,
                "plot_scale": 1
            }
            for key, value in defaults.items():
                if key not in process_info["visualization"]:
                    process_info["visualization"][key] = value
        
        # Setting up legends standard
        if "legend" in process_info and process_info["legend"]:
            defaults = {
                "LegendStyle": "l",
                "LegendName": process_info.get('name', 'unknown'),
                "ShowOption": True,
            }
            for key, value in defaults.items():
                if key not in process_info["legend"]:
                    process_info["legend"][key] = value
        
        # Each process should have a description.
        # If not provided by user or left empty, add a default description.
        if "description" not in process_info or not process_info["description"]:
            process_info["description"] = f"Process named '{process_info.get('name', 'unknown')}' for category '{process_info.get('category', 'unknown')}'."
        
        self.data["processes"].append(process_info)
        out(f"{tag} Successfully added process '{name}' (category: '{category}') to the configuration.\n")
    
    def update_weights_and_k_factors(self):
        """
        Recalculate weights and K-factors for all slices based on current configuration
        """
        for process in self.data["processes"]:
            for slice_info in process["events"]:
                n_events = root_events_number_reader(slice_info["directories"])
                slice_info["number_events"] = n_events
                
                # (3) Read systematics for this slice if provided
                if "systematics_file" in slice_info and slice_info["systematics_file"]:

                    syst_data = mg5_parton_systematics_txt_reader(slice_info["systematics_file"])

                    slice_info["cross_section"] = syst_data["Cross Section"]
                    slice_info["qcd_scale_variation"] = syst_data["Scale Variation"]
                    slice_info["central scheme_variation"] = syst_data["Central Scheme Variation"]
                    slice_info["pdf_variation"] = syst_data["PDF Variation"]
                    
                    # Calculate weight and k-factor for this slice
                    if n_events and n_events > 0:

                        lum = self.data["integrated_luminosity/pb"]
                        cross_section = syst_data["Cross Section"]
                        weight = (cross_section * lum) / n_events
                        slice_info["weight"] = weight
                        slice_info["effective_luminosity/pb"] = n_events / cross_section
                        
                        # Calculate K-factor for this slice if NLO cross-section is provided
                        if "nlo_cross_section" in process and process["nlo_cross_section"]:
                            k_factor = process["nlo_cross_section"] / cross_section
                            slice_info["k_factor"] = k_factor
                        else:
                            slice_info["k_factor"] = 1.0
    
    def save_config(self, filepath):
        """
        Save configuration to JSON file
        """
        with open(filepath, 'w') as f:
            json.dump(self.data, f, indent=4)
    
    def load_config(self, filepath):
        """
        Load configuration from JSON file
        """
        with open(filepath, 'r') as f:
            return json.load(f)

    def get_process_by_name(self, process_name):
        """
        Get process by name
        """
        for proc in self.data["processes"]:
            if proc["name"] == process_name:
                return proc
        return None
    


    
