import ROOT
from Tools.ConfigurationManager import Configurator

# Create a new configuration
config = Configurator()
config.set_luminosity(400.0 * 1e3) # pb^-1

# tt production

config.add_process({
    "category": "Background",
    "sub_category": "Multitop", 
    "name": "tt",
    "nlo_systematics_file": "/data/ammelsayed/Framework/Samples/sm_backgrounds/tt_NLO/Events/run_01/parton_systematics.log",
    "data" : {
        "generator" : "MadGraph5", 
        "directory": "/data/ammelsayed/Framework/Samples/sm_backgrounds/tt"
    },
    # "events": [
    #     {   
    #         "directories": "/data/ammelsayed/Framework/Samples/sm_backgrounds/tt",
    #         # "phase_space_cuts": [],
    #         # "systematics_file": "/data/ammelsayed/Framework/Samples/sm_backgrounds/tt/Events/run_P1/parton_systematics.log",
    #         # "slice_label": "inclusive"
    #     }
    # ],
    "visualization": {"plot_scale": 1},
    "legend": {"LegendName":"t#bar{t}", "ShowOption": True, "LegendStyle": "f"},
    "description": "Top pair production with phase space slicing"
})

# WW production
config.add_process({
    "category": "Background",
    "sub_category": "Diboson",
    "name": "WW",
    "order": "LO", 
    "nlo_systematics_file": "/data/ammelsayed/Framework/Samples/sm_backgrounds/WW_NLO/Events/run_01/parton_systematics.log",
    "data" : {
        "generator" : "MadGraph5", 
        "directory": "/data/ammelsayed/Framework/Samples/sm_backgrounds/WW"
    },
    "visualization": {"plot_scale": 1},
    "legend": {"LegendName":"WW", "ShowOption": True, "LegendStyle": "f"},
    "description": "Inclusive WW production"
})

# WZ production
config.add_process({
    "category": "Background",
    "sub_category": "Diboson",
    "name": "WZ",
    "order": "LO", 
    "nlo_systematics_file": "/data/ammelsayed/Framework/Samples/sm_backgrounds/WZ_NLO/Events/run_01/parton_systematics.log",
    "data" : {
        "generator" : "MadGraph5", 
        "directory": "/data/ammelsayed/Framework/Samples/sm_backgrounds/WZ"
    },
    "visualization": {"plot_scale": 1},
    "legend": {"LegendName":"WZ", "ShowOption": True, "LegendStyle": "f"},
    "description": "Inclusive WZ production"
})

# ZZ production
config.add_process({
    "category": "Background",
    "sub_category": "Diboson",
    "name": "ZZ",
    "order": "LO", 
    "nlo_systematics_file": "/data/ammelsayed/Framework/Samples/sm_backgrounds/ZZ_NLO/Events/run_01/parton_systematics.log",
    "data" : {
        "generator" : "MadGraph5", 
        "directory": "/data/ammelsayed/Framework/Samples/sm_backgrounds/ZZ"
    },
    "visualization": {"plot_scale": 1},
    "legend": {"LegendName":"ZZ", "ShowOption": True, "LegendStyle": "f"},
    "description": "Inclusive ZZ production"
})

# Triboson production
config.add_process({
    "category": "Background",
    "sub_category": "Triboson",
    "name": "VVV",
    "order": "LO", 
    "nlo_systematics_file": "/data/ammelsayed/Framework/Samples/sm_backgrounds/VVV_NLO/Events/run_01/parton_systematics.log",
    "data" : {
        "generator" : "MadGraph5", 
        "directory": "/data/ammelsayed/Framework/Samples/sm_backgrounds/VVV"
    },
    "visualization": {"plot_scale": 1},
    "legend": {"LegendName":"VVV", "ShowOption": True, "LegendStyle": "f"},
    "description": "Inclusive VVV production"
})

# W + jets production
config.add_process({
    "category": "Background",
    "sub_category": "V+jets",
    "name": "w+jets",
    "order": "LO", 
    "data" : {
        "generator" : "MadGraph5", 
        "directory": "/data/ammelsayed/Framework/Samples/sm_backgrounds/w+_jets"
    },
    "visualization": {"plot_scale": 1},
    "legend": {"LegendName":"W^{+}+jets", "ShowOption": True, "LegendStyle": "f"},
    "description": "Inclusive W+ (+ jets) production"
})

config.add_process({
    "category": "Background",
    "sub_category": "V+jets",
    "name": "w-jets",
    "order": "LO", 
    "data" : {
        "generator" : "MadGraph5", 
        "directory": "/data/ammelsayed/Framework/Samples/sm_backgrounds/w-_jets"
    },
    "visualization": {"plot_scale": 1},
    "legend": {"LegendName":"W^{-}+jets", "ShowOption": True, "LegendStyle": "f"},
    "description": "Inclusive W- (+ jets) production"
})

config.add_process({
    "category": "Background",
    "sub_category": "V+jets",
    "name": "z_jets",
    "order": "LO", 
    "data" : {
        "generator" : "MadGraph5", 
        "directory": "/data/ammelsayed/Framework/Samples/sm_backgrounds/z_jets"
    },
    "visualization": {"plot_scale": 1},
    "legend": {"LegendName":"Z+jets", "ShowOption": True, "LegendStyle": "f"},
    "description": "Inclusive Z + jets production"
})


# Add Signals
sig_plotting_scale = 300

for mass in range(1000, 2000+50, 50):
    config.add_process({
        "category": "Signal",
        "sub_category": "Signal",
        "name": f"sig{mass}",
        "order": "LO", 
        "data" : {
            "generator" : "MadGraph5", 
            "directory": [f"/data/ammelsayed/Framework/MC_Samples/signals/Signal_NewModel/Events/run_M{mass}_B{i}" for i in range(1,6)]
        },
        "visualization": {
                "LineColor": ROOT.kRed + 1 if mass in [1000, 1200] else 0, 
                "LineWidth": 3 if mass in [1000, 1200] else 0,
                "LineStyle": 1 if mass == 1000 else 2 if mass == 1200 else 0,
                "FillColor": ROOT.kRed  if mass in [1000, 1200] else 0,
                "FillStyle": 1 if mass in [1000, 1200] else 0,
                "plot_scale": sig_plotting_scale
            },

        "legend": {
            "LegedStyle": "l",
            "LegendName": f"Signal ({round(mass/1000,2)} TeV) #times {sig_plotting_scale}",
            "ShowOption": True if mass in [1000, 1200] else False
            },

        "description": f"Signal events for heavy leptons mass equal {mass}"
    })


config.save_config("analysis_config.json")
print("\nConfiguration saved to 'analysis_config.json'")

