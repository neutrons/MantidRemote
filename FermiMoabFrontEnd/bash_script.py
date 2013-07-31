'''
Generates a bash script suitable for calling Mantid python scripts on Fermi.
The script template is below and substitutions for certain things (like the
name of the python script to run) are made before saving the file.  
'''


script_template = '''
#!/usr/bin/bash
#
# Script suitable for calling a python script from within a Mantid-MPI environment
#
# Note: Any string bracketed by 2 'at' signs is a keyword that will be replaced
# with an actual value suitable for the particular job submission.  Nothing
# surrounded by 2 'at' signs should actually show up in this bash script
# once it's written to Fermi.
#

# Set the variables that 'module load mantid-mpi' would normally set
# (Make sure you use the -x param to mpirun to pass the variables that
# the compute nodes need over to them.)
PATH=/usr/lib64/compat-openmpi/bin:$PATH
LD_LIBRARY_PATH=/usr/lib64/compat-openmpi/lib:$LD_LIBRARY_PATH
PYTHONPATH=/usr/lib64/python2.6/site-packages/compat-openmpi:$PYTHONPATH
MPI_BIN=/usr/lib64/compat-openmpi/bin
MPI_SYSCONFIG=/etc/compat-openmpi-x86_64
MPI_FORTRAN_MOD_DIR=/usr/lib64/gfortran/modules/compat-openmpi-x86_64
MPI_INCLUDE=/usr/include/compat-openmpi-x86_64
MPI_LIB=/usr/lib64/compat-openmpi/lib
MPI_MAN=/usr/share/man/compat-openmpi-x86_64
MPI_PYTHON_SITEARCH=/usr/lib64/python2.6/site-packages/compat-openmpi
MPI_COMPILER=compat-openmpi-x86_64
MPI_SUFFIX=_compat_openmpi
MPI_HOME=/usr/lib64/compat-openmpi


PREFIX=/sw/fermi/mantid-mpi/mantid-mpi-2.4.0-1.el6.x86_64
PATH=$PATH:$PREFIX/bin
# Second one is to pick up boostmpi (not openmpi itself which comes from the compat package above)
LD_LIBRARY_PATH=$PREFIX/lib:/usr/lib64/openmpi/lib:$LD_LIBRARY_PATH
PYTHONPATH=$PREFIX/bin:$PYTHONPATH

# Compute resources
NUM_NODES=@@NUM_NODES@@
CORES_PER_NODE=@@CORES_PER_NODE@@ 
TOTAL_PROCESSES=$((NUM_NODES * CORES_PER_NODE))

# Switch to the transaction directory created for this job
pushd @@TRANSACTION_DIRECTORY@@ > /dev/null

# Kick off python on the computes...
$MPI_BIN/mpirun -n $TOTAL_PROCESSES -npernode $CORES_PER_NODE -hostfile $PBS_NODEFILE -x PATH=$PATH -x LD_LIBRARY_PATH=$LD_LIBRARY_PATH -x PYTHONPATH=$PYTHONPATH python ./@@PYTHON_JOB_SCRIPT@@

# Return to the original directory
# (Not sure this is necessary since the process is going to end anyway...)
popd > /dev/null
'''

class ScriptSubstitutionError( Exception):
    '''
    Exception raised when a substitution string in the template above
    is left un-processed.
    '''
    
    
def generate_bash_script( **kwargs):
    '''
    Generates a bash script suitable for calling Mantid python scripts on Fermi.
    The script template is above and substitutions for certain things (like the
    name of the python script to run) are made before saving the file.  

    Returns the template (with substitutions) as a string.
    This is used by the submit view.
    '''
    
    script = script_template
    for arg in kwargs:
        script = script.replace( '@@%s@@'%arg, str(kwargs[arg]))
        
    # Sanity check: make sure we haven't left any un-substituted strings...
    if script.find( '@@') != -1:
        raise ScriptSubstitutionError, 'Failed to provide substitution variable for %s'%script[script.find('@@'):].split()[0]
    
    return script