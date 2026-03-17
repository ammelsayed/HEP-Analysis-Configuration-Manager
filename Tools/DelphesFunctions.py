

## -------------------------------------------------------------------------- ##
##    Author:    A.M.M Elsayed                                                ##
##    Email:     ahmedphysica@outlook.com                                     ##
##    Institute: University of Science and Technology of China                ##
## -------------------------------------------------------------------------- ##                        



import ROOT
import os

delphes_path = ".... include pass ...."
ROOT.gInterpreter.AddIncludePath(delphes_path)
ROOT.gInterpreter.AddIncludePath(f"{delphes_path}/classes")
ROOT.gInterpreter.AddIncludePath(f"{delphes_path}/external")
ROOT.gSystem.Load("libDelphes")
ROOT.gInterpreter.Declare('#include "classes/DelphesClasses.h"')
ROOT.gInterpreter.Declare('#include "classes/SortableObject.h"')
ROOT.gInterpreter.Declare('#include "external/ExRootAnalysis/ExRootTreeReader.h"')

ROOT.gROOT.SetBatch(True)

## logging method
tag = "[Delphes_Functions]"
# out = logger.msg if logger is not None else print
out = print

def root_events_number_reader(filepath):

    """
    This function reads a .root file and returns the number of events in the "Delphes" TTree. If the file cannot be opened or does not contain the "Delphes" TTree, it returns None.

    Args:
        filepath (str): Path to the .root file.
    """

    if isinstance(filepath, str):

        file = ROOT.TFile.Open(filepath)

        if not file or file.IsZombie():
            return None

        else:
            try:
                tree = file.Get("Delphes")
                return tree.GetEntries()

            except Exception as e:

                out(f"{tag} Error reading TTree 'Delphes' from file: {filepath}. Exception: {e}")

                return None

    # Need improvment in case that one file in the list of filepaths cannot be opened or does not contain the "Delphes" TTree, currently it will just ignore this file and continue with the rest of the files in the list, but it would be better to return None or raise an exception if any of the files in the list cannot be opened or does not contain the "Delphes" TTree.      
    elif isinstance(filepath, list):

        total_events = 0

        for file in filepath:

            f = ROOT.TFile.Open(file)

            if not f or f.IsZombie():
                continue

            else:
                try:
                    t = f.Get("Delphes")
                    total_events += t.GetEntries()

                except Exception as e:
                    pout(f"{tag} Error reading TTree 'Delphes' from file: {filepath}. Exception: {e}")

        return total_events


def is_healty(root_file_path):

    """
    Check if a ROOT file is healthy (can be opened and is not a zombie)
    """
    f = ROOT.TFile.Open(root_file_path)
    return False if not f or f.IsZombie() else True



def get_root_files_from_directory(directory):
    """
    Get all healthy ROOT files from given directories, with health check
    """

    root_files = []

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".root"):
                full_path = os.path.join(root, file)
                # Check if the file is healthy before adding it
                if is_healty(full_path):
                    root_files.append(full_path)
                else:
                    # Error message for unhealthy file, but continue with the rest of the files
                    out(f"{tag} Skipping unhealthy ROOT file: {full_path}")
    
    return root_files
